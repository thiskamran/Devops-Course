# tests/test_state_management.py
import unittest
import requests
import time
import logging
from unittest.mock import patch, MagicMock
from flask import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestStateManagement(unittest.TestCase):
    BASE_URL = "http://nginx:8197/"
    auth = ("user", "test@123")

    def put_state(self, state):
        return requests.put(
            f"{self.BASE_URL}/state",
            data=state,
            headers={'Content-Type': 'text/plain'},
            auth=self.auth
        )

    def get_state(self):
        return requests.get(f"{self.BASE_URL}/state", auth=self.auth)

    def make_request(self):
        return requests.get(f"{self.BASE_URL}/request", auth=self.auth)
    
    def test_state_management_feature(self):
        """Test the basic state management feature - GET/PUT /state"""
        try:
            # Test initial state
            logger.info("Getting initial state...")
            response = requests.get(f"{self.BASE_URL}/state", auth=self.auth)  
            logger.info(f"Initial state: {response.text}")
            self.assertEqual(response.status_code, 200)
            
            # Test changing state to RUNNING
            logger.info("Attempting to change state to RUNNING...")
            response = requests.put(
                f"{self.BASE_URL}/state",
                data="RUNNING",
                headers={'Content-Type': 'text/plain'},
                auth=self.auth
            )
            logger.info(f"PUT response status: {response.status_code}")
            logger.info(f"PUT response content: {response.text}")
            self.assertEqual(response.status_code, 200)
            
            time.sleep(5)  # Allow state to propagate
            
            # Verify state changed
            response = requests.get(f"{self.BASE_URL}/state", auth=self.auth)
            logger.info(f"Final state: {response.text}")
            print(f"Final state: {response.text}")
            self.assertEqual(response.text.strip(), "RUNNING")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def test_request_handling_in_paused_state(self):
        """Test that requests are blocked in PAUSED state"""
        # Set RUNNING first
        self.put_state("RUNNING")
        response = self.make_request()
        self.assertEqual(response.status_code, 200)
        
        # Change to PAUSED
        self.put_state("PAUSED")
        response = self.make_request()
        self.assertEqual(response.status_code, 503)

    
        """Test behavior when state changes while processing requests"""
        self.put_state("RUNNING")
        time.sleep(1)
        
        # Start a long-running request
        def long_request():
            return requests.get(f"{self.BASE_URL}/request?delay=5", auth=self.auth)
            
        import threading
        request_thread = threading.Thread(target=long_request)
        request_thread.start()
        
        # Change state while request is processing
        time.sleep(1)
        self.put_state("PAUSED")
        
        request_thread.join()
        
        # Verify system is in PAUSED state
        response = self.get_state()
        self.assertEqual(response.text.strip(), "PAUSED")

    def test_run_log_format(self):
        """Test run-log endpoint returns correct format"""
        self.put_state("RUNNING")
        time.sleep(1)
        self.put_state("PAUSED")
        time.sleep(1)
        
        response = requests.get(f"{self.BASE_URL}/run-log", auth=self.auth)
        self.assertEqual(response.status_code, 200)
        
        # Check format of each line
        lines = response.text.strip().split('\n')
        for line in lines:
            # Format: 2025-01-24T14.30:52.940Z: RUNNING->RUNNING
            self.assertRegex(line, 
                r'\d{4}-\d{2}-\d{2}T\d{2}\.\d{2}:\d{2}\.\d{3}Z: [A-Z]+\->[A-Z]+')

    def test_request_endpoint(self):
        """Test GET /request endpoint returns system info as plain text"""
        self.put_state("RUNNING")
        
        response = requests.get(f"{self.BASE_URL}/request", auth=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/plain')
        
        # Verify data format
        self.assertIn("Disk Space", response.text)
        self.assertIn("IP", response.text)
        self.assertIn("Service2", response.text)

    # def test_shutdown_state(self):
    #     """Test SHUTDOWN state behavior"""
    #     try:
    #     # First set to RUNNING
    #         self.put_state("RUNNING")
    #         time.sleep(2)
            
    #         # Initial request should succeed
    #         init_response = self.make_request()
    #         self.assertEqual(init_response.status_code, 200)
            
    #         # Change to SHUTDOWN
    #         logger.info("Changing state to SHUTDOWN...")
    #         response = self.put_state("SHUTDOWN")
    #         self.assertEqual(response.status_code, 200)
            
    #         # Allow shutdown sequence to start
    #         time.sleep(2)
            
    #         # Verify state is SHUTDOWN
    #         state_response = self.get_state()
    #         self.assertEqual(state_response.text.strip(), "SHUTDOWN")
            
    #         # Verify requests are rejected
    #         shutdown_response = self.make_request()
    #         self.assertEqual(shutdown_response.status_code, 503)
            
    #         # Try to reach service2 (should fail as it's shutting down)
    #         try:
    #             service2_response = requests.get("http://service2:8080")
    #             self.assertNotEqual(service2_response.status_code, 200)
    #         except requests.exceptions.RequestException:
    #             # Connection error is expected as service2 should be shutting down
    #             pass
                
    #         # Verify service1 instances are shutting down by checking multiple endpoints
    #         endpoints = [
    #             "http://service1:8199/request",
    #             "http://service2:8080",
    #         ]
            
    #         time.sleep(5)  # Give time for shutdown to propagate
            
    #         for endpoint in endpoints:
    #             try:
    #                 response = requests.get(endpoint)
    #                 self.assertNotEqual(response.status_code, 200, f"Endpoint {endpoint} should not be available")
    #             except requests.exceptions.RequestException:
    #                 # Connection errors are expected during shutdown
    #                 pass
                    
    #         logger.info("Shutdown test completed successfully")
            
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Test shutdown state failed: {str(e)}")
    #         raise


if __name__ == '__main__':
    unittest.main()