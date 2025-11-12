import numpy
import sys
import ctypes

from PySide6.QtCore import (
    QEvent,
    QFile,
    QIODevice,
    QPointF,
    QRectF,
    QSize,
    qFatal,
    qWarning,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QGradient,
    QImage,
    QMatrix4x4,
    QPainter,
    QPlatformSurfaceEvent,
    QSurface,
    QWindow,
    QRhiNativeHandles,
)
from PySide6.QtGui import (
    QRhi,
    QRhiBuffer,
    QRhiDepthStencilClearValue,
    QRhiGraphicsPipeline,
    QRhiNullInitParams,
    QRhiD3D12InitParams,
    QRhiD3D12NativeHandles,
    QRhiRenderBuffer,
    QRhiShaderResourceBinding,
    QRhiSampler,
    QRhiTexture,
    QRhiShaderStage,
    QRhiVertexInputAttribute,
    QRhiVertexInputBinding,
    QRhiVertexInputLayout,
    QRhiViewport,
    QShader,
)

from PySide6.support import VoidPtr

# fmt: off
# Y up (note clipSpaceCorrMatrix in m_viewProjection), CCW
VERTEX_DATA = numpy.array([
    0.0, 0.5, 1.0, 0.0, 0.0,
    -0.5, -0.5, 0.0, 1.0, 0.0,
    0.5, -0.5, 0.0, 0.0, 1.0], dtype=numpy.float32)
# fmt: on
UBUF_SIZE = 68


def getShader(name):
    f = QFile(name)
    if f.open(QIODevice.OpenModeFlag.ReadOnly):
        result = QShader.fromSerialized(f.readAll())
        f.close()
        return result
    return QShader()


class RhiWindow(QWindow):
    def __init__(self, graphicsApi, render_app):
        super().__init__()
        self.render_app = render_app
        self.m_graphicsApi = QRhi.Implementation.Null
        self.m_initialized = False
        self.m_notExposed = False
        self.m_newlyExposed = False
        self.m_fallbackSurface = None
        self.m_rhi = None
        self.m_sc = None
        self.m_ds = None
        self.m_rp = None
        self.m_hasSwapChain = False
        self.m_viewProjection = QMatrix4x4()
        self.m_graphicsApi = graphicsApi

        if graphicsApi == QRhi.Implementation.D3D12:
            self.setSurfaceType(QSurface.SurfaceType.Direct3DSurface)
        elif graphicsApi == QRhi.Implementation.Null:
            pass  # RasterSurface

    def __del__(self):
        # destruction order matters to a certain degree: the fallbackSurface
        # must outlive the rhi, the rhi must outlive all other resources.
        # The resources need no special order when destroying.
        del self.m_rp
        self.m_rp = None
        del self.m_ds
        self.m_ds = None
        del self.m_sc
        self.m_sc = None
        del self.m_rhi
        self.m_rhi = None
        if self.m_fallbackSurface:
            del self.m_fallbackSurface
            self.m_fallbackSurface = None

    def graphicsApiName(self):
        if self.m_graphicsApi == QRhi.Implementation.Null:
            return "Null (no output)"
        if self.m_graphicsApi == QRhi.Implementation.OpenGLES2:
            return "OpenGL"
        if self.m_graphicsApi == QRhi.Implementation.Vulkan:
            return "Vulkan"
        if self.m_graphicsApi == QRhi.Implementation.D3D11:
            return "Direct3D 11"
        if self.m_graphicsApi == QRhi.Implementation.D3D12:
            return "Direct3D 12"
        if self.m_graphicsApi == QRhi.Implementation.Metal:
            return "Metal"
        return ""

    def customInit(self):
        pass

    def customRender(self):
        pass

    def exposeEvent(self, e):
        # initialize and start rendering when the window becomes usable
        # for graphics purposes
        is_exposed = self.isExposed()
        if is_exposed and not self.m_initialized:
            self.init()
            self.resizeSwapChain()
            self.m_initialized = True

        surfaceSize = self.m_sc.surfacePixelSize() if self.m_hasSwapChain else QSize()

        # stop pushing frames when not exposed (or size is 0)
        if (
            (not is_exposed or (self.m_hasSwapChain and surfaceSize.isEmpty()))
            and self.m_initialized
            and not self.m_notExposed
        ):
            self.m_notExposed = True

        # Continue when exposed again and the surface has a valid size. Note
        # that surfaceSize can be (0, 0) even though size() reports a valid
        # one, hence trusting surfacePixelSize() and not QWindow.
        if (
            is_exposed
            and self.m_initialized
            and self.m_notExposed
            and not surfaceSize.isEmpty()
        ):
            self.m_notExposed = False
            self.m_newlyExposed = True

        # always render a frame on exposeEvent() (when exposed) in order to
        # update immediately on window resize.
        if is_exposed and not surfaceSize.isEmpty():
            self.render()

    def event(self, e):
        if e.type() == QEvent.Type.UpdateRequest:
            self.render()
        elif e.type() == QEvent.Type.PlatformSurface:
            # this is the proper time to tear down the swapchain (while
            # the native window and surface are still around)
            if (
                e.surfaceEventType()
                == QPlatformSurfaceEvent.SurfaceEventType.SurfaceAboutToBeDestroyed
            ):  # noqa: E501
                self.releaseSwapChain()

        return super().event(e)

    def init(self):
        if self.m_graphicsApi == QRhi.Implementation.Null:
            params = QRhiNullInitParams()
            self.m_rhi = QRhi.create(QRhi.Implementation.Null, params)

        elif self.m_graphicsApi == QRhi.Implementation.D3D12:
            handles = QRhiD3D12NativeHandles()
            params = QRhiD3D12InitParams()
            params.enableDebugLayer = False
            # handles.dev = ctypes.c_void_p(self.render_app.GetDeviceNativeHandle())
            handles.minimumFeatureLevel = 0
            handles.adapterLuidHigh = self.render_app.GetDxAdapterLuidHigh()
            handles.adapterLuidLow = self.render_app.GetDxAdapterLuidLow()
            # handles.commandQueue = ctypes.c_void_p(self.render_app.GetStreamNativeHandle())

            flag = QRhi.Flag()
            self.m_rhi = QRhi.create(QRhi.Implementation.D3D12, params, flag, handles)

        if not self.m_rhi:
            qFatal("Failed to create RHI backend")

        self.m_sc = self.m_rhi.newSwapChain()
        # no need to set the size here, due to UsedWithSwapChainOnly
        self.m_ds = self.m_rhi.newRenderBuffer(
            QRhiRenderBuffer.Type.DepthStencil,
            QSize(),
            1,
            QRhiRenderBuffer.Flag.UsedWithSwapChainOnly,
        )
        self.m_sc.setWindow(self)
        self.m_sc.setDepthStencil(self.m_ds)
        self.m_rp = self.m_sc.newCompatibleRenderPassDescriptor()
        self.m_sc.setRenderPassDescriptor(self.m_rp)
        self.customInit()

    def resizeSwapChain(self):
        self.m_hasSwapChain = self.m_sc.createOrResize()  # also handles self.m_ds
        outputSize = self.m_sc.currentPixelSize()
        self.m_viewProjection = self.m_rhi.clipSpaceCorrMatrix()
        r = float(outputSize.width()) / float(outputSize.height())
        self.m_viewProjection.perspective(45.0, r, 0.01, 1000.0)
        self.m_viewProjection.translate(0, 0, -4)

    def releaseSwapChain(self):
        if self.m_hasSwapChain:
            self.m_hasSwapChain = False
            self.m_sc.destroy()

    def render(self):
        if not self.m_hasSwapChain or self.m_notExposed:
            return

        # If the window got resized or newly exposed, resize the swapchain.
        # (the newly-exposed case is not actually required by some platforms,
        # but is here for robustness and portability)
        #
        # This (exposeEvent + the logic here) is the only safe way to perform
        # resize handling. Note the usage of the RHI's surfacePixelSize(), and
        # never QWindow::size(). (the two may or may not be the same under the
        # hood, # depending on the backend and platform)
        if (
            self.m_sc.currentPixelSize() != self.m_sc.surfacePixelSize()
            or self.m_newlyExposed
        ):
            self.resizeSwapChain()
            if not self.m_hasSwapChain:
                return
            self.m_newlyExposed = False

        result = self.m_rhi.beginFrame(self.m_sc)
        if result == QRhi.FrameOpResult.FrameOpSwapChainOutOfDate:
            self.resizeSwapChain()
            if not self.m_hasSwapChain:
                return
            result = self.m_rhi.beginFrame(self.m_sc)

        if result != QRhi.FrameOpResult.FrameOpSuccess:
            qWarning(f"beginFrame failed with {result}, will retry")
            self.requestUpdate()
            return

        self.customRender()

        self.m_rhi.endFrame(self.m_sc)

        # Always request the next frame via requestUpdate(). On some platforms
        # this is backed by a platform-specific solution, e.g. CVDisplayLink
        # on macOS, which is potentially more efficient than a timer,
        # queued metacalls, etc.
        self.requestUpdate()


class HelloWindow(RhiWindow):
    def __init__(self, graphicsApi, render_app):
        super().__init__(graphicsApi, render_app)
        self.m_vbuf = None
        self.m_ubuf = None
        self.m_texture = None
        self.m_sampler = None
        self.m_colorTriSrb = None
        self.m_colorPipeline = None
        self.m_fullscreenQuadSrb = None
        self.m_fullscreenQuadPipeline = None
        self.m_initialUpdates = None

        self.m_rotation = 0
        self.m_opacity = 1
        self.m_opacityDir = -1

    def ensureFullscreenTexture(self, pixelSize, u):
        if self.m_texture and self.m_texture.pixelSize() == pixelSize:
            return

        if not self.m_texture:
            self.m_texture = self.m_rhi.newTexture(QRhiTexture.Format.RGBA8, pixelSize)
        else:
            self.m_texture.setPixelSize(pixelSize)

        handle = self.render_app.create_texture(pixelSize.width(), pixelSize.height)
        self.m_texture.create()

    def customInit(self):
        self.m_initialUpdates = self.m_rhi.nextResourceUpdateBatch()

        vertex_size = 4 * VERTEX_DATA.size
        self.m_vbuf = self.m_rhi.newBuffer(
            QRhiBuffer.Type.Immutable, QRhiBuffer.UsageFlag.VertexBuffer, vertex_size
        )
        self.m_vbuf.create()
        self.m_initialUpdates.uploadStaticBuffer(
            self.m_vbuf, VoidPtr(VERTEX_DATA.tobytes(), vertex_size)
        )

        self.m_ubuf = self.m_rhi.newBuffer(
            QRhiBuffer.Type.Dynamic, QRhiBuffer.UsageFlag.UniformBuffer, UBUF_SIZE
        )
        self.m_ubuf.create()

        self.ensureFullscreenTexture(
            self.m_sc.surfacePixelSize(), self.m_initialUpdates
        )

        self.m_sampler = self.m_rhi.newSampler(
            QRhiSampler.Filter.Linear,
            QRhiSampler.Filter.Linear,
            QRhiSampler.Filter.None_,
            QRhiSampler.AddressMode.ClampToEdge,
            QRhiSampler.AddressMode.ClampToEdge,
        )
        self.m_sampler.create()

        self.m_colorTriSrb = self.m_rhi.newShaderResourceBindings()
        visibility = (
            QRhiShaderResourceBinding.StageFlag.VertexStage
            | QRhiShaderResourceBinding.StageFlag.FragmentStage
        )
        bindings = [QRhiShaderResourceBinding.uniformBuffer(0, visibility, self.m_ubuf)]
        self.m_colorTriSrb.setBindings(bindings)
        self.m_colorTriSrb.create()

        self.m_colorPipeline = self.m_rhi.newGraphicsPipeline()
        # Enable depth testing; not quite needed for a simple triangle, but we
        # have a depth-stencil buffer so why not.
        self.m_colorPipeline.setDepthTest(True)
        self.m_colorPipeline.setDepthWrite(True)
        # Blend factors default to One, OneOneMinusSrcAlpha, which is convenient.
        premulAlphaBlend = QRhiGraphicsPipeline.TargetBlend()
        premulAlphaBlend.enable = True
        self.m_colorPipeline.setTargetBlends([premulAlphaBlend])
        stages = [
            QRhiShaderStage(QRhiShaderStage.Type.Vertex, getShader(":/color.vert.qsb")),
            QRhiShaderStage(
                QRhiShaderStage.Type.Fragment, getShader(":/color.frag.qsb")
            ),
        ]
        self.m_colorPipeline.setShaderStages(stages)
        inputLayout = QRhiVertexInputLayout()
        input_bindings = [QRhiVertexInputBinding(5 * 4)]  # sizeof(float)
        inputLayout.setBindings(input_bindings)
        attributes = [
            QRhiVertexInputAttribute(0, 0, QRhiVertexInputAttribute.Format.Float2, 0),
            # sizeof(float)
            QRhiVertexInputAttribute(
                0, 1, QRhiVertexInputAttribute.Format.Float3, 2 * 4
            ),
        ]
        inputLayout.setAttributes(attributes)
        self.m_colorPipeline.setVertexInputLayout(inputLayout)
        self.m_colorPipeline.setShaderResourceBindings(self.m_colorTriSrb)
        self.m_colorPipeline.setRenderPassDescriptor(self.m_rp)
        self.m_colorPipeline.create()

        self.m_fullscreenQuadSrb = self.m_rhi.newShaderResourceBindings()
        bindings = [
            QRhiShaderResourceBinding.sampledTexture(
                0,
                QRhiShaderResourceBinding.StageFlag.FragmentStage,  # noqa: E501
                self.m_texture,
                self.m_sampler,
            )
        ]
        self.m_fullscreenQuadSrb.setBindings(bindings)
        self.m_fullscreenQuadSrb.create()

        self.m_fullscreenQuadPipeline = self.m_rhi.newGraphicsPipeline()
        stages = [
            QRhiShaderStage(QRhiShaderStage.Type.Vertex, getShader(":/quad.vert.qsb")),
            QRhiShaderStage(
                QRhiShaderStage.Type.Fragment, getShader(":/quad.frag.qsb")
            ),
        ]
        self.m_fullscreenQuadPipeline.setShaderStages(stages)
        layout = QRhiVertexInputLayout()
        self.m_fullscreenQuadPipeline.setVertexInputLayout(layout)
        self.m_fullscreenQuadPipeline.setShaderResourceBindings(
            self.m_fullscreenQuadSrb
        )
        self.m_fullscreenQuadPipeline.setRenderPassDescriptor(self.m_rp)
        self.m_fullscreenQuadPipeline.create()

    def customRender(self):
        resourceUpdates = self.m_rhi.nextResourceUpdateBatch()

        if self.m_initialUpdates:
            resourceUpdates.merge(self.m_initialUpdates)
            self.m_initialUpdates = None

        self.m_rotation += 1.0
        modelViewProjection = self.m_viewProjection
        modelViewProjection.rotate(self.m_rotation, 0, 1, 0)
        projection = numpy.array(modelViewProjection.data(), dtype=numpy.float32)
        resourceUpdates.updateDynamicBuffer(self.m_ubuf, 0, 64, projection.tobytes())

        self.m_opacity += self.m_opacityDir * 0.005
        if self.m_opacity < 0.0 or self.m_opacity > 1.0:
            self.m_opacityDir *= -1
            self.m_opacity = max(0.0, min(1.0, self.m_opacity))

        opacity = numpy.array([self.m_opacity], dtype=numpy.float32)
        resourceUpdates.updateDynamicBuffer(self.m_ubuf, 64, 4, opacity.tobytes())

        cb = self.m_sc.currentFrameCommandBuffer()
        outputSizeInPixels = self.m_sc.currentPixelSize()

        # (re)create the texture with a size matching the output surface size,
        # when necessary.
        self.ensureFullscreenTexture(outputSizeInPixels, resourceUpdates)

        cv = QRhiDepthStencilClearValue(1.0, 0)
        cb.beginPass(
            self.m_sc.currentFrameRenderTarget(),
            Qt.GlobalColor.black,
            cv,
            resourceUpdates,
        )

        cb.setGraphicsPipeline(self.m_fullscreenQuadPipeline)
        viewport = QRhiViewport(
            0, 0, outputSizeInPixels.width(), outputSizeInPixels.height()
        )
        cb.setViewport(viewport)
        cb.setShaderResources()
        cb.draw(3)

        cb.setGraphicsPipeline(self.m_colorPipeline)
        cb.setShaderResources()
        vbufBinding = (self.m_vbuf, 0)
        cb.setVertexInput(0, [vbufBinding])
        cb.draw(3)
        cb.endPass()
