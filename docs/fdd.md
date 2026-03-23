# Functional Design Document (FDD)

## Introduction  
This document outlines the functional requirements and specifications of the system to ensure clarity and alignment among stakeholders.

### Purpose  
The purpose of this FDD is to detail the functionalities that will be implemented in the system, providing a comprehensive understanding of the expected features and operations.

### Requirements  
1. **AI News Fetcher Module**  
   - The module fetches the latest AI-related news articles from Google News RSS and displays them in CLI or GUI modes. It supports search queries and article count limitations in the output.  
   - Evidence Path: "ai_news_module.py"

2. **Calculator Operations**  
   - The calculator supports operations such as addition, subtraction, multiplication, division, power, modulus, square root, and percentage calculations. Each operation must be validated for correctness (e.g., no division/modulus by zero, and negative square roots).  
   - Evidence Path: "calculator.py"

3. **User Interface**  
   - The calculator must support both CLI and GUI modes. The GUI should allow operations selection and display results accordingly.  
   - Evidence Path: "calculator.py"

4. **Calendar Module**  
   - The calendar module allows users to display today's date via CLI or GUI.  
   - Evidence Path: "calendar_module.py"

5. **Date Display Functionality**  
   - The calendar module includes functionality to show today's date either in the command line interface or in a graphical interface.  
   - Evidence Path: "calendar_module.py"

6. **Test Module**  
   - The test module verifies the integrity and correctness of the functionalities through various test cases.  
   - Evidence Path: "test"

## Use Cases  
### Fetch AI News  
- **Actor**: User  
- **Precondition**: User has opened the AI news module (CLI or GUI).  
- **Postcondition**: The latest AI news articles are displayed.  
- **Flow**:  
  1. User specifies a search query and number of articles (if needed).  
  2. System fetches and displays the results.  
   
   Evidence Path: "ai_news_module.py"

### Perform Calculator Operation  
- **Actor**: User  
- **Precondition**: User has opened the calculator app (CLI or GUI).  
- **Postcondition**: The calculator displays the result of the performed operation.  
- **Flow**:  
  1. User selects operation (e.g., add, sub).  
  2. User inputs the numbers.  
  3. System calculates and returns the result, displaying it in the console or GUI.  
   
   Evidence Path: "calculator.py"

### Display Today's Date  
- **Actor**: User  
- **Precondition**: User has opened the calendar module (CLI or GUI).  
- **Postcondition**: The current date is displayed to the user.  
- **Flow**:  
  1. User selects CLI or GUI mode.  
  2. System retrieves today's date.  
  3. System displays the date to the user.  
   
   Evidence Path: "calendar_module.py"

### Run Tests  
- **Actor**: Developer  
- **Precondition**: Developer has the test module set up.  
- **Postcondition**: The test results are displayed showing the outcomes of the tests.  
- **Flow**:  
  1. Developer runs the test module.  
  2. System executes various test cases against different functionalities.  
  3. The results of the tests are displayed for review.  
   
   Evidence Path: "test"

## Conclusion  
This FDD sets the foundation for the system's construction based on the outlined functional requirements.