#include <nanobind/nanobind.h>
#include <nanobind/stl/function.h>
#include <nanobind/stl/pair.h>
// #include <nanobind/stl/string.h>
// #include <nanobind/stl/vector.h>

namespace nb = nanobind;
using namespace nb::literals;

NB_MODULE(lc_engine_ext, m) {
    m.doc() = "LuisaCompute Engine Python Extension";
    m.def("test", []() { return "Hello"; });
}