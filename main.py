import sys
import os

dll_file = os.path.abspath("./build/windows/x64/release/")
sys.path.append(dll_file)

try:
    import lc_engine_ext
except:
    print("lc_engine_ext not valid")


def main():
    print(lc_engine_ext.__doc__)
    print("Hello from lcqtsample!")
    print(lc_engine_ext.test())

    from lc_engine_ext import App

    print(App.__doc__)


if __name__ == "__main__":
    main()
