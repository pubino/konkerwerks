import os
import sys
import time
import logging
import subprocess
from ccworks.browser_client import ConcurBrowserClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test():
    # 1. Start mock server in thread
    from tests.mock_concur_server import MockConcurServer, REPORTS
    logger.info("Starting mock SAP Concur server on port 8091 (threaded)...")
    server = MockConcurServer(port=8091)
    server.start() # This starts the thread internally
    
    # Wait for server to be responsive
    time.sleep(1)
    
    # Sanity check: verify REPORTS is populated
    logger.info(f"Sanity check: REPORTS has {len(REPORTS)} items.")

    try:
        client = ConcurBrowserClient(base_url="http://127.0.0.1:8091")
        report_name = "Existing Report"

        print("\n============================================================")
        print("      RUNNING TRANSACTION ALLOCATION CRUD TESTS")
        print("============================================================\n")

        # Step 1: Read existing allocations (should be empty)
        print("[Step 1] Reading initial allocations for transaction 0...")
        alloc_res = client.get_transaction_allocations(report_name, 0, headless=True)
        if alloc_res["success"]:
            print(f"         Initial allocations: {alloc_res['allocations']}")
            assert len(alloc_res["allocations"]) == 0, "Expected 0 initial allocations"
            print("         [PASS] Initial empty check.")
        else:
            print(f"         [FAIL] Failed to read allocations: {alloc_res.get('error')}")
            return

        # Step 2: Add an allocation
        dept = "(25605) ORF-Technical Support"
        fund = "(A0001) General Fund"
        prog = "(P999) Research"
        print(f"[Step 2] Adding allocation: Dept={dept}, Fund={fund}, Prog={prog}...")
        add_res = client.add_transaction_allocation(report_name, 0, dept, fund, prog, headless=True)
        if add_res["success"]:
            print("         [PASS] Allocation added successfully.")
        else:
            print(f"         [FAIL] Failed to add allocation: {add_res.get('error')}")
            return

        # Step 3: Verify the allocation exists
        print("[Step 3] Verifying newly added allocation...")
        verify_res = client.get_transaction_allocations(report_name, 0, headless=True)
        if verify_res["success"]:
            found_allocs = verify_res["allocations"]
            print(f"         Allocations found: {found_allocs}")
            # The mock server renders: "Dept: (25605) ORF-Technical Support | Fund: (A0001) General Fund | Prog: (P999) Research"
            match = any(dept in a["raw_text"] and fund in a["raw_text"] for a in found_allocs)
            assert match, f"Could not find expected allocation in {found_allocs}"
            print("         [PASS] Allocation verified.")
        else:
            print(f"         [FAIL] Failed to verify allocation: {verify_res.get('error')}")
            return

        print("\n============================================================")
        print("             ALL ALLOCATION TESTS PASSED")
        print("============================================================\n")

    finally:
        logger.info("Stopping mock SAP Concur server...")
        server.stop()

if __name__ == "__main__":
    run_test()
