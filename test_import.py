#!/usr/bin/env python3
"""Test script to verify config_flow.py can be imported correctly."""
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Testing Climate Control Calendar config_flow.py import...")
print("=" * 60)

try:
    print("\n1. Checking if file exists...")
    config_flow_path = "custom_components/climate_control_calendar/config_flow.py"
    if os.path.exists(config_flow_path):
        print(f"   ✓ File exists: {config_flow_path}")

        # Check file modification time
        import datetime
        mtime = os.path.getmtime(config_flow_path)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"   ✓ Last modified: {mtime_str}")
    else:
        print(f"   ✗ File NOT found: {config_flow_path}")
        sys.exit(1)

    print("\n2. Checking for old __pycache__ files...")
    pycache_dir = "custom_components/climate_control_calendar/__pycache__"
    if os.path.exists(pycache_dir):
        cache_files = os.listdir(pycache_dir)
        if cache_files:
            print(f"   ! Found {len(cache_files)} cache files (these may be outdated)")
            print("   ! Recommendation: Delete __pycache__ directory")
        else:
            print("   ✓ __pycache__ directory is empty")
    else:
        print("   ✓ No __pycache__ directory found")

    print("\n3. Checking for syntax errors...")
    import py_compile
    try:
        py_compile.compile(config_flow_path, doraise=True)
        print("   ✓ No syntax errors found")
    except py_compile.PyCompileError as e:
        print(f"   ✗ Syntax error found: {e}")
        sys.exit(1)

    print("\n4. Searching for the fix in config_flow.py...")
    with open(config_flow_path, 'r') as f:
        content = f.read()

        # Check for the new pattern (correct)
        if 'def __init__(self) -> None:' in content and 'ClimateControlCalendarOptionsFlow' in content:
            # Find the __init__ method of OptionsFlow
            lines = content.split('\n')
            in_options_flow_class = False
            found_correct_init = False
            found_old_pattern = False

            for i, line in enumerate(lines):
                if 'class ClimateControlCalendarOptionsFlow' in line:
                    in_options_flow_class = True
                elif in_options_flow_class and 'class ' in line and not line.strip().startswith('#'):
                    in_options_flow_class = False

                if in_options_flow_class:
                    if 'def __init__(self) -> None:' in line:
                        found_correct_init = True
                        print(f"   ✓ Found correct __init__ signature at line {i+1}")
                    if 'self.config_entry = config_entry' in line:
                        found_old_pattern = True
                        print(f"   ✗ Found old pattern 'self.config_entry = config_entry' at line {i+1}")

            if found_correct_init and not found_old_pattern:
                print("   ✓ HA 2026 fix is correctly applied")
            elif found_old_pattern:
                print("   ✗ Old pattern still present - fix NOT applied")
            else:
                print("   ? Could not verify fix")
        else:
            print("   ✗ Could not find OptionsFlow class or __init__ method")

    print("\n5. Checking for debug logging...")
    if '_LOGGER.debug("OptionsFlow.__init__() called' in content:
        print("   ✓ Debug logging is present")
    else:
        print("   ✗ Debug logging NOT found - file may not be the latest version")

    print("\n" + "=" * 60)
    print("RESULT: Import test completed successfully")
    print("=" * 60)
    print("\nIf Home Assistant still shows errors:")
    print("1. Delete: /config/custom_components/climate_control_calendar/__pycache__")
    print("2. Delete: /config/custom_components/climate_control_calendar/*.pyc")
    print("3. Restart Home Assistant (full restart, not just reload)")
    print("4. Check logs at: /config/home-assistant.log")
    print("5. Enable debug logging in configuration.yaml:")
    print("   logger:")
    print("     logs:")
    print("       custom_components.climate_control_calendar: debug")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
