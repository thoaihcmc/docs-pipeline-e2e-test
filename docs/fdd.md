# Functional Design Document (FDD)

## Introduction  
This document outlines the functional requirements and specifications of the system to ensure clarity and alignment among stakeholders.

### Purpose  
The purpose of this FDD is to detail the functionalities that will be implemented in the system, providing a comprehensive understanding of the expected features and operations.

### Requirements  
1. **User Authentication**  
   - Users must be able to create accounts and log in securely.  
   - Evidence Path: "requirements.txt"

2. **Data Management**  
   - The system should allow users to manage data effectively, including CRUD operations.  
   - Evidence Path: "config.py"

3. **Reporting**  
   - Users must have the capability to generate reports based on the data inputted.  
   - Evidence Path: "config.py"

4. **Calculator Operations**  
   - The calculator supports operations such as addition, subtraction, multiplication, division, power, modulus, square root, and percentage calculations. Each operation must be validated for correctness (e.g., no division/modulus by zero, and negative square roots).  
   - Evidence Path: "calculator.py"

5. **User Interface**  
   - The calculator must support both CLI and GUI modes. The GUI should allow operations selection and display results accordingly.  
   - Evidence Path: "calculator.py"

## Use Cases  
### Create User Account  
- **Actor**: User  
- **Precondition**: The user is on the registration page.  
- **Postcondition**: A new user account is created in the system.  
- **Flow**:  
  1. User fills out the registration form.  
  2. User submits the form.  
  3. System validates the input and creates the account.  
   
   Evidence Path: "requirements.txt"

### Perform Calculator Operation  
- **Actor**: User  
- **Precondition**: User has opened the calculator app (CLI or GUI).  
- **Postcondition**: The calculator displays the result of the performed operation.  
- **Flow**:  
  1. User selects operation (e.g., add, sub).  
  2. User inputs the numbers.  
  3. System calculates and returns the result, displaying it in the console or GUI.  

    Evidence Path: "calculator.py"

## Conclusion  
This FDD sets the foundation for the system's construction based on the outlined functional requirements.