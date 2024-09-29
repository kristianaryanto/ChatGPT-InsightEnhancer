import logging
from textwrap import dedent
from typing import Iterable

import openai
import streamlit as st
import tiktoken


def analyze_code_files(code_files: list[str]) -> Iterable[dict[str, str]]:
    """Analyze the selected code files and return recommendations."""
    return (analyze_code_file(code_file) for code_file in code_files)


def analyze_code_file(code_file: str) -> dict[str, str]:
    """Analyze a code file and return a dictionary with file information and recommendations."""
    with open(code_file, "r") as f:
        code_content = f.read()

    if not code_content:
        return {
            "code_file": code_file,
            "code_snippet": code_content,
            "recommendation": "No code found in file",
        }

    try:
        logging.info("Analyzing code file: %s", code_file)
        analysis = get_code_analysis(code_content)
    except Exception as e:
        logging.info("Error analyzing code file: %s", code_file)
        analysis = f"Error analyzing code file: {e}"

    return {
        "code_file": code_file,
        "code_snippet": code_content,
        "recommendation": analysis,
    }


import tiktoken
import logging

def get_num_tokens_from_messages(messages, model="gpt-4o-mini"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logging.debug("Model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Define token costs based on model type
    if model == "gpt-3.5-turbo":
        logging.debug(
            "gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301."
        )
        return get_num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        logging.debug(
            "gpt-4 may change over time. Returning num tokens assuming gpt-4-0314."
        )
        return get_num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-4o-mini":
        # Assumed token structure for gpt-4o-mini
        tokens_per_message = 3  # Customize this based on expected behavior
        tokens_per_name = 1
    else:
        raise NotImplementedError(
            f"num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."
        )

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name

    # Assumes every conversation is primed with a start message token count
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

    return num_tokens


@st.cache_data(show_spinner=False)
def get_code_analysis(code: str) -> str:
    """Get code analysis from the OpenAI API."""
    prompt = dedent(
        f"""\

Please review the provided code and identify any **syntax or logical errors**, suggest **refactoring improvements** to enhance code quality, recommend **performance optimizations**, address any **security vulnerabilities**, and ensure alignment with **best practices**. Additionally, highlight **potential bugs** that could emerge during runtime or in edge cases.

For each point, provide concise feedback, and when relevant, offer **code suggestions** to demonstrate the fix or improvement. Use the prompts provided for each section to structure your responses effectively.

**Note**: Limit your recommendations to 30 per category. If applicable, include line numbers to make the feedback actionable.

---

Response format:

---

**Syntax and logical errors**:  
- Highlight syntax issues, such as missing parentheses or improper indentation.
- Look for logical issues where conditions may never be true, or variables are misused.
- If there is an issue with variable assignment or function calls, correct it with an example.

Example:
```python
# Original
if x = 5:  
    do_something()

# Corrected
if x == 5:  
    do_something()
```

---

**Code refactoring and quality**:  
- Recommend extracting repetitive logic into separate functions to reduce duplication.
- Suggest restructuring code to improve readability, like replacing deep nesting with guard clauses.
- Propose using better data structures or design patterns to make the code more maintainable.

Example:
```python
# Original: Repetitive code in an if-else block
if user.role == 'admin':
    return 'Admin access'
elif user.role == 'editor':
    return 'Editor access'
else:
    return 'Viewer access'

# Refactored: Use a dictionary lookup
roles = 
    'admin': 'Admin access',
    'editor': 'Editor access',
    'viewer': 'Viewer access'

return roles.get(user.role, 'Viewer access')
```

---

**Performance optimization**:  
- Look for inefficient loops or expensive calculations that can be optimized.
- Suggest using more efficient algorithms or data structures (e.g., switching from `O(n^2)` to `O(n log n)`).
- Propose caching results of expensive operations if they are used multiple times.

Example:
```python
# Original: Repeated expensive operation inside a loop
for item in items:
    expensive_result = calculate_expensive_operation(item)
    process(expensive_result)

# Optimized: Cache the result outside the loop
expensive_result_cache = calculate_expensive_operation(items)
for item in items:
    process(expensive_result_cache)
```

---

**Security vulnerabilities**:  
- Point out vulnerabilities such as SQL injection, XSS, or hardcoded sensitive data.
- Recommend using safer coding practices, like prepared statements for SQL queries.
- Propose using encryption, secure communication protocols, or proper validation for inputs.

Example:
```python
# Original: SQL query vulnerable to injection
query = f"SELECT * FROM users WHERE username = 'username'"

# Secure version: Use prepared statements
cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```

---



**Possible bugs**:  
- Look for off-by-one errors, uncaught exceptions, or issues with unhandled edge cases.
- Recommend adding error handling, boundary checks, or modifying loops to prevent such bugs.
- If the logic could break with certain inputs, suggest a safer implementation.

Example:
```python
# Original: Off-by-one error in loop
for i in range(len(items)):
    print(items[i+1])

# Bug fix: Adjust loop to prevent accessing out-of-range index
for i in range(len(items)-1):
    print(items[i+1])
```

---

**Best practices**:  
- Suggest consistent naming conventions (e.g., camelCase vs snake_case) throughout the code.
- Encourage adding meaningful comments or docstrings, especially in complex functions.
- Recommend writing unit tests or adding error handling where appropriate.

Example:
```python
# Original: Inconsistent naming and no docstrings
def calculateSum():
    return 0

def calculate_total_sum():
    pass

# Best practice: Consistent naming and docstring added
def calculate_sum():
    
    Function to calculate the sum of values.
    
    return 0
```

---

**Recommendation Code**:  
- Provide a final compiled section that integrates all the review comments into one **revised code example**.
- Ensure that the combined feedback (syntax fixes, refactoring, performance optimization, and best practices) is implemented in this final code block.
- This section should serve as the final, improved version of the provided code, with all recommendations applied.

Example:
```python
# Final compiled code with all recommendations applied
def calculate_sum_of_users():
    ```
    This function calculates and returns the sum of all active users.
    It also checks for valid user role before calculation.
    ```

    # Mapping of user roles
    roles = 
        'admin': 'Admin access',
        'editor': 'Editor access',
        'viewer': 'Viewer access'
    

    # Cached expensive operation outside loop
    expensive_result_cache = calculate_expensive_operation(users)

    # Refactored loop for processing users with added error handling
    for user in users:
        try:
            if user.role not in roles:
                raise ValueError(f"Unknown role: user.role")
            process(expensive_result_cache)

        except Exception as e:
            print(f"Error processing user user.id: e")

# Secure SQL query using prepared statements
def get_user_by_username(username):
    cursor.execute("SELECT * FROM users WHERE username = s", (username,))
    return cursor.fetchone()

# Best practice: added docstrings and consistent naming conventions
def update_user_profile(user_id, profile_data):
    ```
    Update user profile information in the database.
    :param user_id: The ID of the user.
    :param profile_data: Dictionary containing user profile updates.
    ```
    # Example logic here
    pass
```

---




Code:
```
{code}
```

Your review:"""
    )
    messages = [{"role": "system", "content": prompt}]
    tokens_in_messages = get_num_tokens_from_messages(
        messages=messages, model="gpt-4o-mini"
    )
    max_tokens = 8192
    tokens_for_response = max_tokens - tokens_in_messages
    print(f"tokens_in_messages: {tokens_in_messages}")
    print(f"max_tokens: {max_tokens}")
    print(f"tokens_for_response: {tokens_for_response}" )


    if tokens_for_response < 200:
        return "The code file is too long to analyze. Please select a shorter file."

    logging.info("Sending request to OpenAI API for code analysis")
    logging.info("Max response tokens: %d", tokens_for_response)
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=tokens_for_response,
        n=1,
        temperature=0,
    )
    logging.info("Received response from OpenAI API")

    # Get the assistant's response from the API response
    assistant_response = response.choices[0].message["content"]

    return assistant_response.strip()
