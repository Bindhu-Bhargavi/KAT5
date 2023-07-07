# SP_FI_KAT_WARM_RST_1 - Single Port Warmreset Functionality Test with IO script
#
# Author: Mobiveil
#
# ©Copyright (2021 - 2022) by Mobiveil Inc, All rights reserved.
"""SP_FI_KAT_WARM_RST_1 - Single Port Warmreset Functionality Test with IO script

Test Information
----------------
    Test Type = Functionality Test with IO
    Port = Single Port
    Cycles Configured = 1000
    Input Combination  =  Fixed T1, T2
    Details = Without log analysis based execution test

Test Objective
--------------
    To Verify the Warmreset with IO on Port 0

Test Requirements
-----------------
    1. Windows 10 Host.
    2. KAT5 Tester Platform
    3. CSS Endpoint / ESS EndPoint in single port mode.
    4. KAT5 Driver package
    5. Change kit

Test Procedure
--------------
    1. Initialize KAT5 Hardware and Driver.
    2. Initiate IO to dual PORT  Endpoint (IO write) on Port 0
    3. Send warmresetCommand with Fixed T1 and T2 Values from application on Port 0.
    4. Wait for Linkup
    5. Disable the EP driver.
    6. Enable the EP driver to recover the EP.
    7. Repeate the steps 2 - 6 for 1000 cycles.

Expected Behaviour
------------------
    After Step 6:
    The DS LTSSM state should be L0.
"""
import os
import sys
import time
from random import randint

_path = os.getcwd()
_path = _path.split('TestFramework')

g_path = os.path.join(_path[0], 'TestFramework')

if g_path not in sys.path:
    sys.path.append(g_path)

from kat5lib import kat, katPrint, INFO, test_status_banner, KatWarmReset, get_file_name, KatPCIeLink, _wait
from kat5lib import SetupTest, compress, check_io, check, IOGenerator, add_test_banner, returncode, KatConfigSpace

with SetupTest('warmreset', 'debug', testid=get_file_name(__file__)) as test:
    add_test_banner(test)

    # Pre-Setup Failed.
    if not test.init_sts:
        test_status_banner("Test Pre-Setup Failed")
        sys.exit(returncode.status_presetup_fail)

    # 0xC0 is for single port.
    if kat.pval != 0xC0:
        test_status_banner(f'Unsupported Bitfile for Single Port test with ID {test.id_} ')
        sys.exit(returncode.status_presetup_fail)

    # recovering the driver before performing IO.
    IOGenerator.fixture_recover()
    time.sleep(1)
    kat.flushetw()
    katPrint(INFO, '|{}|\n'.format('*' * 93))

    warmreset = KatWarmReset(p0opcode=0x7)
    p0t1delay = randint(2000000, 3000000)
    p0t2delay = randint(2000000, 3000000)

    ### Pcie link details.
    pcie = KatPCIeLink(waittime=5)
    orig_capability = hex(kat.p0_capability)
    p0genlw = (int(orig_capability[-1]), int(orig_capability[-2]))

    Iteration_count = 1000
    g_status = []
    cycle = 1
    while 1:
        if cycle > Iteration_count:
            break
        katPrint(INFO, f"Count= {cycle}\n")

        status = pcie.get(port='0', verify=False)
        if not status:
            test_status_banner("Failed to get pcie link details")
        g_status.append(status)

        status = IOGenerator.start_io_gen(port='0', mode='read', direction='sequential', workers=100, size=4096)
        time.sleep(1.5)
        status &= check_io('0', port='0', instance='before') if status else 0
        if status:
            status = warmreset.trigger(p0t1delay=p0t1delay, p0t2delay=p0t2delay, port='0')
            status &= check_io('0', port='0', instance='after') if status else 0
            if status:
                katPrint(INFO, "Kat Warm Reset Trigger Success\n")
            else:
                test_status_banner("Kat Warm Reset Trigger Failed")
            katPrint(INFO, '|{}|\n'.format('*' * 93))

        IOGenerator.stop()
        IOGenerator.recover_disk()

        ## Get Pcie link details after IO.
        status = pcie.get(port='0', verify=False)
        if (p0genlw == pcie.p0gen_lw):
            status = True
            katPrint(INFO, "GenSpeed and Lanewidths are same before and after IO\n")
        else:
            status = False
            test_status_banner("GenSpeed and Lanewidths are not same before and after IO")
        g_status.append(status)

        ## To Check the link stability
        config_read = KatConfigSpace()
        config_read.check_stability()

        kat.flushetw()

        if cycle != Iteration_count:
            katPrint(INFO, '|{}|\n'.format('*' * 93))
        cycle += 1

        if not check(g_status):
            test_status_banner("Intermediate Failure Happened")
            break

    test.test_status = check(g_status)

compress(test)
if not test.test_status:
    sys.exit(returncode.status_fail)
