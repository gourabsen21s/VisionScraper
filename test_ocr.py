#!/usr/bin/env python3
"""Test OCR text extraction"""

from runner.perception.yolo_perception import YOLOPerception
import os

perception = YOLOPerception()
screenshot_dir = '/tmp/browser_runner_artifacts'

if os.path.exists(screenshot_dir):
    sessions = sorted(os.listdir(screenshot_dir))
    print(f'Available sessions: {sessions[-3:]}')  # Show last 3
    latest_session = sessions[-1]
    print(f'Using session: {latest_session}')
    session_dir = os.path.join(screenshot_dir, latest_session)
    
    # Check all step files
    step_files = [f for f in os.listdir(session_dir) if f.startswith('step_') and f.endswith('.png')]
    step_files.sort()
    print(f'Step files: {step_files}')
    
    for step_file in step_files:
        screenshot_path = os.path.join(session_dir, step_file)
        print(f'\n=== {step_file} ===')
        
        if os.path.exists(screenshot_path):
            elements = perception.analyze(screenshot_path)
            print(f'Total elements: {len(elements)}')
            
            # Show elements with text
            text_elements = [(i, elem) for i, elem in enumerate(elements) if elem.text.strip()]
            print(f'Elements with text: {len(text_elements)}')
            
            for i, elem in text_elements[:5]:  # Show first 5
                print(f'  {i+1}. {elem.type}: "{elem.text}" at {elem.bbox}')
                
            # Show field elements specifically
            field_elements = [(i, elem) for i, elem in enumerate(elements) if elem.type == 'field']
            print(f'Field elements: {len(field_elements)}')
            for i, elem in field_elements:
                print(f'  Field {i+1}: "{elem.text}" at {elem.bbox}')
