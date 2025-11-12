import sys
import os

dll_path = os.path.abspath("build/windows/x64/release/")
sys.path.append(dll_path)

try:
    import lc_engine_ext
except:
    print("lc_engine_ext not valid")

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication, QRhi, QSurfaceFormat, QRhiNativeHandles

from rhi_window import HelloWindow
import rhi_window_rc  # noqa: F401


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    render_app = lc_engine_ext.App()
    print(render_app.__doc__)
    render_app.create_context(dll_path)
    backend = "dx"
    render_app.init(backend)

    graphicsApi = QRhi.Implementation.D3D12
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)

    window = HelloWindow(graphicsApi, render_app)

    window.resize(1280, 720)
    title = QCoreApplication.applicationName() + " - " + window.graphicsApiName()
    window.setTitle(title)
    window.show()

    ret = app.exec()
    if window.isVisible():
        window.releaseSwapChain()

    sys.exit(ret)
