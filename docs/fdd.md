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

6. **Authentication Module**  
   - The authentication module manages user registration, login, and session management. It must ensure user data integrity and security through hashing and storage in the SQLite database.  
   - Evidence Path: "auth_module.py"

7. **Configuration Handling**  
   - The configuration module provides settings for approved paths, document requirements, and function to access those paths.  
   - Evidence Path: "config.py"

8. **User Testing Module**  
   - A testing module exists to validate functionality for all components in the previous files.  
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

### User Authentication  
- **Actor**: User  
- **Precondition**: User must be logged in to access certain modules.  
- **Postcondition**: The user session is validated, and access is granted if authenticated.  
- **Flow**:  
  1. System checks for an active session.  
  2. If no session exists, the user is prompted to log in or register.  
  3. System validates user credentials and provides access.  
   
   Evidence Path: "auth_module.py"

### User Testing  
- **Actor**: Developer/Tester  
- **Precondition**: The testing module is executed.  
- **Postcondition**: Results of the test cases are displayed to verify functionality.  
- **Flow**:  
  1. Test cases are executed.  
  2. Results are logged and displayed.  
   
   Evidence Path: "test"

## Conclusion  
This FDD sets the foundation for the system's construction based on the outlined functional requirements.