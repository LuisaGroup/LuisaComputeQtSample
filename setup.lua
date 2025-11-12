function main(lc_path, qt_path)
    if type(lc_path) ~= "string" or not os.exists(lc_path) then
        utils.error("LuisaCompute path illegal.")
        return
    end
    if type(qt_path) ~= "string" or not os.exists(qt_path) then
        utils.error("QT path illegal.")
        return
    end




    local lc_options = {
        lc_cuda_backend = true,
        lc_dx_backend = true,
        lc_vk_backend = true,
        lc_enable_dsl = true,
        lc_enable_gui = true,
        lc_metal_backend = false,
        lc_enable_mimalloc = true,
        lc_enable_custom_malloc = false,
        lc_enable_unity_build = true,
        lc_enable_simd = true,
        lc_enable_api = false,
        lc_enable_clangcxx = false,
        lc_enable_osl = false,
        lc_enable_ir = false,
        lc_enable_tests = false,
        lc_external_marl = false,
        lc_dx_cuda_interop = false,
        lc_backend_lto = false
    }

    local py_options = {}
    local py_cfg_file = ".venv/pyvenv.cfg"
    local f = io.open(py_cfg_file, "r")
    if f ~= nil then 
        print("uv python env exist, using python env")
        local home_line = f:read()
        local home_path = string.sub(home_line, 8)
        home_path = home_path:gsub('\\', '/')
        print("using python env: ", home_path) -- C:\Users ...
        lc_options["lc_py_include"] = "\"" .. home_path .. "/include" .. "\""
        local lc_py_linkdir = home_path .. "/libs"
        lc_options["lc_py_linkdir"] = "\"" .. lc_py_linkdir .. "\""
        local files = {}
        local sb = ""
        local py = "python"
        for _, filepath in ipairs(os.files(path.join(lc_py_linkdir, "*.lib"))) do
            local lib_name = path.basename(filepath)
            if #lib_name >= #py and lib_name:sub(1, #py):lower() == py then
                table.insert(files, lib_name)
            end
        end
        if #files > 0 then
            for i, v in ipairs(files) do
                sb = sb .. v .. ";"
            end
        end
        lc_options["lc_py_libs"] = "\"" .. sb .. "\""
    else 
        print("uv python env does not exist, skip python binding")
    end
    -- write sdk-dir
    lc_path = lc_path:gsub('\\', '/')
    qt_path = qt_path:gsub('\\', '/')
    lc_options.lc_sdk_dir = "'" .. path.join(lc_path, "SDKs"):gsub('\\', '/') .. "'"

    local file = io.open("lc_options.generated.lua", "w")
    file:write("lc_dir = '")
    file:write(lc_path)
    file:write("'\n")

    file:write("qt_path = '")
    file:write(qt_path)
    file:write("'\n")
    file:write("lc_options = {\n")

    for key, value in pairs(lc_options) do
        file:write("    " .. key .. " = " .. tostring(value) .. ",\n")
    end
    
    file:write("}\n")
    file:close()
end
