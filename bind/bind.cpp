#include <nanobind/nanobind.h>
#include <nanobind/stl/function.h>
#include <nanobind/stl/pair.h>
#include "dummyrt.h"

namespace nb = nanobind;
using namespace nb::literals;

NB_MODULE(lc_engine_ext, m) {
    m.doc() = "LuisaCompute Engine Python Extension";
    m.def("test", []() { return "Hello"; });

    auto cls =
        nb::class_<App>(
            m, "App", "LuisaCompute Engine App")
            .def(nb::init<>())
            .def("create_context", &App::create_context)
            .def("init", &App::init)
            .def("create_texture", &App::create_texture)
            .def("update", &App::update)
            .def("handle_key", &App::handle_key)
            .def("GetDeviceNativeHandle", &App::GetDeviceNativeHandle)
            .def("GetVkPhysicalDevice", &App::GetVkPhysicalDevice)
            .def("GetDxAdapterLuidHigh", &App::GetDxAdapterLuidHigh)
            .def("GetDxAdapterLuidLow", &App::GetDxAdapterLuidLow)
            .def("GetStreamNativeHandle", &App::GetStreamNativeHandle)
            .def("init_vulkan", &App::init_vulkan);

    if (!nb::type<App>().is(cls))
        nb::detail::raise("type lookup failed!");
}