# Implementation Plan

## Bug 1: Airflow Substring Matching

- [ ] 1. Write bug condition exploration test for Airflow substring matching
  - **Property 1: Fault Condition** - Airflow Experience Returns "2" Instead of "0"
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the substring matching bug
  - **Scoped PBT Approach**: Scope the property to questions containing "airflow" (case-insensitive)
  - Test that `_handle_experience_question()` with questions containing "Airflow" returns answer="2" with reasoning containing "ai" (from Fault Condition in design)
  - The test assertions should match the Expected Behavior: answer="0" with reasoning about no Airflow experience
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: questions like "¿Cuántos años de experiencia tienes en Airflow?" return "2" instead of "0"
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [ ] 2. Write preservation property tests for existing technology responses (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Technology Experience Responses
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for technologies with real experience (Python, SQL, AWS, Ruby, machine learning)
  - Write property-based tests capturing observed behavior: Python→"5", Ruby→"3", SQL→"4", AWS→"2", machine learning→"2"
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.5_

- [ ] 3. Fix for Airflow substring matching bug

  - [ ] 3.1 Implement the fix in `_handle_experience_question`
    - Sort tech_experience dictionary by key length (descending) before iteration
    - Ensure 'airflow' entry exists with value '0' in tech_experience dictionary
    - Optionally use word boundaries (regex) for exact matching
    - Add logging to show which technology matched and in what order
    - _Bug_Condition: isBugCondition_Airflow(input) where 'airflow' IN question_lower AND 'ai' matches before 'airflow'_
    - _Expected_Behavior: answer="0" with reasoning about no Airflow experience_
    - _Preservation: Technologies with real experience (Python, SQL, AWS, Ruby) continue returning correct years_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.5_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Airflow Experience Returns "0"
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Technology Experience Responses
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

## Bug 2: CV Radio Button Detection Failure

- [ ] 4. Write bug condition exploration test for CV radio button detection
  - **Property 1: Fault Condition** - CV Radio Buttons Not Detected
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the detection failure
  - **Scoped PBT Approach**: Create mock modal HTML with CV radio buttons matching LinkedIn structure
  - Test that `detect_fields()` with modal containing radio buttons returns 0 fields (from Fault Condition in design)
  - The test assertions should match the Expected Behavior: detect and return FormField objects with field_type='cv_radio'
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: selector 'input[id*="jobsDocumentCardToggle"]' returns empty list
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.3, 1.4, 2.3, 2.4_

- [ ] 5. Write preservation property tests for other field detection (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Field Detection
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-CV fields (text, numeric, email, phone, dropdown, textarea)
  - Write property-based tests capturing observed detection behavior for each field type
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.4_

- [ ] 6. Fix for CV radio button detection failure

  - [ ] 6.1 Inspect LinkedIn DOM and update selector
    - Manually inspect LinkedIn page with pre-uploaded CVs to identify correct selector
    - Update FIELD_TYPES['cv_radio'] in FormFieldDetector with correct selector
    - Consider alternative selectors: 'input[type="radio"][id*="document"]', 'label.jobs-document-upload-redesign-card__container input[type="radio"]'
    - Add fallback selectors if primary selector fails
    - _Bug_Condition: isBugCondition_CVRadio(input) where modal has CV radio buttons but selector returns []_
    - _Expected_Behavior: detect_fields() returns FormField objects with field_type='cv_radio' for each available CV_
    - _Preservation: Other field types (text, numeric, email, phone, dropdown, textarea) continue being detected correctly_
    - _Requirements: 1.3, 1.4, 2.3, 2.4, 3.3, 3.4_

  - [ ] 6.2 Add explicit wait for radio buttons to render
    - Import WebDriverWait and expected_conditions in FormFieldDetector
    - Add wait logic in detect_fields() for cv_radio field type
    - Wait up to 5 seconds for radio buttons to be present
    - Handle TimeoutException gracefully with debug logging
    - _Requirements: 2.3, 2.4_

  - [ ] 6.3 Add detailed logging for CV radio button detection
    - Log when no radio buttons found with expected selector
    - Log modal HTML snippet (first 500 chars) for debugging
    - Log number of radio buttons found when successful
    - _Requirements: 2.3, 2.4_

  - [ ] 6.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - CV Radio Buttons Detected
    - **IMPORTANT**: Re-run the SAME test from task 4 - do NOT write a new test
    - The test from task 4 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 4
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.3, 2.4_

  - [ ] 6.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Field Detection
    - **IMPORTANT**: Re-run the SAME tests from task 5 - do NOT write new tests
    - Run preservation property tests from step 5
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

## Bug 3: CV Selection Ignoring AI Recommendation

- [ ] 7. Write bug condition exploration test for CV selection ignoring AI
  - **Property 1: Fault Condition** - CV Selection Ignores AI and Pre-loaded CVs
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the selection bug
  - **Scoped PBT Approach**: Mock scenario with pre-loaded CVs and job requiring specific CV type
  - Test that `handle_cv_upload()` searches for input[type='file'] first and uploads new file (from Fault Condition in design)
  - The test assertions should match the Expected Behavior: check for existing CVs, call select_cv_by_keywords(), select matching radio button
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: system uploads new file even when matching CV exists
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.5, 1.6, 1.7, 2.5, 2.6, 2.7_

- [ ] 8. Write preservation property tests for CV upload without pre-loaded CVs (BEFORE implementing fix)
  - **Property 2: Preservation** - CV Upload When No Pre-loaded CVs
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code when no CVs are pre-loaded (only input[type='file'] exists)
  - Write property-based tests capturing observed upload behavior: system uploads appropriate CV file
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.6, 3.7_

- [ ] 9. Fix for CV selection ignoring AI recommendation

  - [ ] 9.1 Refactor handle_cv_upload() to check for existing CVs first
    - Reorder logic: check for radio buttons BEFORE searching for input[type='file']
    - Search for CV radio buttons using selector from Bug 2 fix
    - Log number of pre-loaded CVs found
    - _Bug_Condition: isBugCondition_CVSelection(input) where modal has pre-loaded CVs but system uploads new file_
    - _Expected_Behavior: verify existing CVs → get AI recommendation → select matching CV → only upload if no match_
    - _Preservation: When no pre-loaded CVs exist, continue uploading appropriate CV file_
    - _Requirements: 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.6, 3.7_

  - [ ] 9.2 Integrate CVSelector and get AI recommendation
    - Ensure CVSelector is instantiated in LinkedInApplier.__init__
    - Call self.cv_selector.select_cv(job.title, job.description) to get recommendation
    - Log the AI recommendation (cv_type, language)
    - Store recommendation for use in selection logic
    - _Requirements: 2.6, 2.7_

  - [ ] 9.3 Implement _matches_recommendation() helper function
    - Create helper function to check if radio button CV matches AI recommendation
    - Extract file name from radio button's parent element
    - Define cv_keywords mapping: 'software' → ['software', 'engineer', 'backend', 'fullstack'], 'engineer' → ['automatización', 'automation', 'data', 'ml', 'ai']
    - Return True if any keyword from recommended cv_type is in file name
    - Handle exceptions gracefully with debug logging
    - _Requirements: 2.6, 2.7_

  - [ ] 9.4 Implement CV selection logic using AI recommendation
    - Iterate through radio buttons found in step 9.1
    - For each radio button, call _matches_recommendation()
    - If match found, click the radio button and return True
    - Log which CV was selected
    - If no match, fall back to uploading new file with input[type='file']
    - _Requirements: 2.5, 2.6, 2.7_

  - [ ] 9.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - CV Selection Uses AI Recommendation
    - **IMPORTANT**: Re-run the SAME test from task 7 - do NOT write a new test
    - The test from task 7 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 7
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.5, 2.6, 2.7_

  - [ ] 9.6 Verify preservation tests still pass
    - **Property 2: Preservation** - CV Upload When No Pre-loaded CVs
    - **IMPORTANT**: Re-run the SAME tests from task 8 - do NOT write new tests
    - Run preservation property tests from step 8
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

## Bug 4: Job Description Expansion False Negative

- [ ] 10. Write bug condition exploration test for description expansion false negative
  - **Property 1: Fault Condition** - Description Expansion Reports False Negative
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the false negative bug
  - **Scoped PBT Approach**: Mock scenario with expandable description button
  - Test that after clicking expand button, system reports "no such element" error (from Fault Condition in design)
  - The test assertions should match the Expected Behavior: click button → wait for content → find with correct selectors → extract successfully
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: content expands but search with .jobs-description__content fails
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.8, 2.8_

- [ ] 11. Write preservation property tests for non-expandable descriptions (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-expandable Descriptions
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for descriptions without expand button
  - Write property-based tests capturing observed behavior: system processes visible description without errors
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.8_

- [ ] 12. Fix for job description expansion false negative

  - [ ] 12.1 Add explicit wait after clicking expand button
    - Import WebDriverWait and expected_conditions
    - After clicking expand button, add WebDriverWait for content to be present
    - Wait up to 5 seconds for .jobs-description__content to appear
    - Handle TimeoutException with warning log
    - Add additional 1 second sleep for complete rendering
    - _Bug_Condition: isBugCondition_DescriptionExpansion(input) where button clicks successfully but content search fails_
    - _Expected_Behavior: click button → wait for rendering → find content with correct selectors → extract successfully_
    - _Preservation: Descriptions without expand button continue processing normally_
    - _Requirements: 1.8, 2.8, 3.8_

  - [ ] 12.2 Update selectors to work post-expansion
    - Verify which selectors work after expansion
    - Update description_selectors list with post-expansion selectors
    - Try more specific selectors: "div.jobs-description__content", "div[class*='jobs-description__content']"
    - Add fallback selectors: "article.jobs-description", "section.jobs-description"
    - _Requirements: 2.8_

  - [ ] 12.3 Improve error handling to avoid false negatives
    - After trying all selectors, check if expand button is still visible
    - If button not visible, assume expansion succeeded
    - Try extracting with more general selector (body.text) as last resort
    - Log success/failure of each step clearly
    - Don't report error if content was actually expanded
    - _Requirements: 2.8_

  - [ ] 12.4 Add detailed logging for expansion process
    - Log "Intentando expandir descripción..."
    - Log "Botón encontrado: {selector}"
    - Log "Clic ejecutado, esperando renderizado..."
    - Log "Buscando contenido con {len(selectors)} selectores..."
    - Log "✓ Descripción extraída: {len(description)} caracteres"
    - _Requirements: 2.8_

  - [ ] 12.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Description Expansion Succeeds
    - **IMPORTANT**: Re-run the SAME test from task 10 - do NOT write a new test
    - The test from task 10 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 10
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.8_

  - [ ] 12.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-expandable Descriptions
    - **IMPORTANT**: Re-run the SAME tests from task 11 - do NOT write new tests
    - Run preservation property tests from step 11
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

## Bug 5: Insufficient Logging for AI Interactions

- [ ] 13. Write bug condition exploration test for insufficient logging
  - **Property 1: Fault Condition** - AI Interactions Not Fully Logged
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the logging bug
  - **Scoped PBT Approach**: Capture logs during answer_question() call
  - Test that logs do NOT contain system_prompt, user_message, raw API response, or parsed JSON (from Fault Condition in design)
  - The test assertions should match the Expected Behavior: logs contain all prompts, responses, and reasoning
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: logs only show "Respondiendo pregunta..." and "Respuesta IA: ..."
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.9, 2.9_

- [ ] 14. Write preservation property tests for other logging (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Logging Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-AI logging (field detection, form filling, navigation)
  - Write property-based tests capturing observed logging patterns
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: (implicit preservation of existing logging)_

- [ ] 15. Fix for insufficient logging of AI interactions

  - [ ] 15.1 Add logging of complete prompts before API call
    - In answer_question(), before self.client.call()
    - Log separator line "=" * 80
    - Log "LLAMADA A OPENROUTER API"
    - Log "SYSTEM PROMPT:\n{system_prompt}"
    - Log separator line "-" * 80
    - Log "USER MESSAGE:\n{user_message}"
    - Log separator line "=" * 80
    - _Bug_Condition: isBugCondition_InsufficientLogging(input) where AI call occurs but prompts not logged_
    - _Expected_Behavior: log complete system_prompt, user_message, API response, parsed JSON, and reasoning_
    - _Preservation: Existing logging for non-AI operations continues unchanged_
    - _Requirements: 1.9, 2.9_

  - [ ] 15.2 Add logging of complete API response
    - After self.client.call() receives response
    - Log separator line "=" * 80
    - Log "RESPUESTA DE OPENROUTER API"
    - Log "RAW RESPONSE:\n{response}"
    - Log separator line "=" * 80
    - _Requirements: 2.9_

  - [ ] 15.3 Add logging of parsed JSON
    - After self.client.extract_json_response(response)
    - Log "JSON PARSEADO:"
    - Log json.dumps(result, indent=2, ensure_ascii=False)
    - Log separator line "=" * 80
    - _Requirements: 2.9_

  - [ ] 15.4 Add logging of reasoning and extracted fields
    - Extract reasoning from result.get('reasoning', 'Respuesta generada por IA')
    - Log "REASONING DEL MODELO: {reasoning}"
    - Log "CONFIDENCE: {confidence}"
    - Log "ANSWER: {answer}"
    - _Requirements: 2.9_

  - [ ] 15.5 Add logging in _handle_experience_question
    - Log "Procesando pregunta de experiencia: {question}"
    - Log sorted technologies (first 5 for brevity)
    - When match found, log "✓ COINCIDENCIA ENCONTRADA: '{tech}' → {years} años"
    - Log "  Pregunta contenía: '{tech}' en '{question_lower}'"
    - If no match, log "No se encontró tecnología específica, usando experiencia general"
    - _Requirements: 2.9_

  - [ ] 15.6 Ensure logging level is configured to INFO
    - Check logging configuration in module or __init__
    - Set logging.basicConfig(level=logging.INFO) if not already set
    - Ensure format includes timestamp, name, level, and message
    - _Requirements: 2.9_

  - [ ] 15.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - AI Interactions Fully Logged
    - **IMPORTANT**: Re-run the SAME test from task 13 - do NOT write a new test
    - The test from task 13 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 13
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.9_

  - [ ] 15.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Logging Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 14 - do NOT write new tests
    - Run preservation property tests from step 14
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

## Final Checkpoint

- [ ] 16. Checkpoint - Ensure all tests pass
  - Run all exploration tests (tasks 1, 4, 7, 10, 13) - all should PASS
  - Run all preservation tests (tasks 2, 5, 8, 11, 14) - all should PASS
  - Verify no regressions in existing functionality
  - Test complete application flow with all 5 fixes integrated
  - Ask the user if questions arise or if manual testing is needed
