target("lc_engine_ext")
    set_extension(".pyd")
    add_deps("nanobind")
    add_rules("lc_basic_settings", {
        project_kind = "shared",
        enable_exception = true,
        rtti = true
    })
    add_files("*.cpp")
target_end()