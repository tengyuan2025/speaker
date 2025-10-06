#!/usr/bin/env python3
"""
Quick fix script for ModelScope dependency issues
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    print("Fixing ModelScope dependencies...")

    # List of commonly missing dependencies
    missing_deps = [
        "addict>=2.4.0",
        "simplejson>=3.19.0",
        "oss2>=2.18.0",
        "sortedcontainers>=2.4.0",
        "yapf>=0.33.0",
        "datasets>=2.14.0",
        "Pillow>=9.0.0",
        "opencv-python>=4.5.0",
        "filelock>=3.12.0",
        "huggingface-hub>=0.16.0",
    ]

    for dep in missing_deps:
        print(f"Installing {dep}...")
        try:
            install_package(dep)
            print(f"  ✓ {dep} installed")
        except Exception as e:
            print(f"  ✗ Failed to install {dep}: {e}")

    # Test ModelScope import
    print("\nTesting ModelScope import...")
    try:
        from modelscope.pipelines import pipeline
        print("✅ ModelScope imported successfully!")
        return 0
    except ImportError as e:
        print(f"❌ Failed to import ModelScope: {e}")
        print("\nTry running:")
        print("  pip install modelscope --upgrade")
        return 1

if __name__ == "__main__":
    sys.exit(main())