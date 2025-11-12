# LuisaCompute+Qt Sample

这是一个样例来展示如何使用LuisaCompute和Qt搭建比较复杂的桌面端样例

make sure Qt 6.6+ installed
- `xmake l setup.lua #LuisaComput dir# #QT-SDK dir#`: Set LC path and valid qt path
- `xmake f -c"` config
- `xmake`: compile
- `xmake run rhi_window_sample dx`, run with Direct3D 12 backend (change to `vk` for Vulkan backend)

结果如图所示，UI组件只是为了展示，没有实际效果

![](doc/result.png)


## Python Example

我们知道Qt6有官方的python绑定PySide6其中也导出了QRhi的接口，我们可以尝试将LuisaCompute所写的运行时导出为python包，在python中进行引擎的绑定，这样的好处是可以将大量的算法实现放在python中，极大提升python本身较为孱弱的GUI能力。

Get Started
- 安装`uv`
- 执行`git submodule update --init --recursive`来下载`ext/nanobind` 
- `uv sync` 同步并初始化python环境