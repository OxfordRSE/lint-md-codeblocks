import os
import re
import subprocess
import sys
import argparse

def get_markdown_files(directory):
    """
    Get all .md files in the specified directory that do not have "slides" in their name.

    Args:
    - directory (str): The directory to search for .md files.

    Returns:
    - list: A list of matching .md file paths.
    """
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') and 'slides' not in root:
                markdown_files.append(os.path.join(root, file))
    return markdown_files

def find_code_blocks(content):
    code_block_pattern = re.compile(
        r"^(\s*)(```|~~~)(.*?)\s*\n(.*?)(^\s*\2\s*$)", re.DOTALL | re.MULTILINE
    )
    parts = []
    last_pos = 0

    for match in code_block_pattern.finditer(content):
        if match.start() > last_pos:
            non_code_content = content[last_pos:match.start()]
            parts.append((False, "", non_code_content))

        leading_spaces = match.group(1)[1:]
        lang_line = match.group(3).strip()
        code = match.group(4)
        end_block = match.group(5)

        stripped_lines = []
        for line in code.split('\n'):
            if line.startswith(' ' * len(leading_spaces)):
                stripped_lines.append(line[len(leading_spaces):])
            else:
                stripped_lines.append(line)
        
        # Add a newline before and after the code block
        parts.append((True, lang_line, '\n' + '\n'.join(stripped_lines)))

        last_pos = match.end()

    if last_pos < len(content):
        non_code_content = content[last_pos:]
        parts.append((False, "", non_code_content))
    return parts

def lint_python(py_content, flake8_config):
    fname = "temp.py"
    with open(fname, 'w') as out:
        out.write(py_content)
    result = subprocess.run(['flake8', f'--config={flake8_config}', fname], capture_output=True, text=True)
    output = result.stdout.strip()
    os.remove(fname)
    return output

def lint_cpp(cpp_content):
    fname = "temp.cpp"
    with open(fname, 'w') as out:
        out.write(cpp_content)
    result = subprocess.run(['cppcheck', fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stderr.strip()  # cppcheck writes warnings and errors to stderr
    os.remove(fname)
    return output

def join_code_blocks(parts, language):
    """
    Join all code block contents together into one string, with other code blocks as comments.

    Args:
    - parts (list): A list of tuples, where each tuple contains a boolean indicating if the block is code, the language, and the block content.
    - language (str): The programming language to filter code blocks by.

    Returns:
    - str: A single string containing all joined code block contents with other code blocks as comments.
    """
    all_blocks = []

    comment_prefix = "# " if language == 'python' else "// "

    for is_code, lang, block in parts:
        if is_code and language in lang and "nolint" not in lang:
            all_blocks.append(block)
        elif is_code:
            # Add other code blocks as comments
            comment_block = "\n".join(comment_prefix + line for line in block.split("\n"))
            all_blocks.append(comment_block)
        else:
            # Add non-code parts as comments
            comment_block = "\n".join(comment_prefix + line for line in block.split("\n"))
            all_blocks.append(comment_block)

    return "\n".join(all_blocks)

def parse_python_output(output):
    """
    Parse the output of flake8 and return error lines with their respective messages.

    Args:
    - output (str): The linter output.

    Returns:
    - list: A list of tuples, where each tuple contains the line number and the error message.
    """
    errors = []
    lines = output.split('\n')
    for line in lines:
        parts = line.split(':')
        if len(parts) > 1:
            try:
                error_line_num = int(parts[1]) - 1
                errors.append((error_line_num, line))
            except ValueError:
                continue
    return errors

def parse_cpp_output(output):
    """
    Parse the output of cppcheck and return error lines with their respective messages.

    Args:
    - output (str): The linter output.

    Returns:
    - list: A list of tuples, where each tuple contains the line number and the error message.
    """
    errors = []
    error_pattern = re.compile(r"temp.cpp:(\d+):\d+: (.+)")
    matches = error_pattern.findall(output)
    for match in matches:
        error_line_num = int(match[0]) - 1
        error_message = match[1]
        errors.append((error_line_num, f"temp.cpp:{match[0]}: {error_message}"))
    return errors

def main(directory, flake8_config, language):
    files = get_markdown_files(directory)
    found_errors = False
    for file in files:
        with open(file, 'r') as f:
            relative_path = os.path.relpath(file, directory)
            content = f.read()
            parts = find_code_blocks(content)
            if not any(is_code for is_code, lang, _ in parts if lang.startswith(language)):
                continue
            content_to_lint = join_code_blocks(parts, language)
            
            if language == 'python' and content_to_lint:
                output = lint_python(content_to_lint, flake8_config)
                errors = parse_python_output(output)
            elif language == 'cpp' and content_to_lint:
                output = lint_cpp(content_to_lint)
                errors = parse_cpp_output(output)
            else:
                raise ValueError(f"Unsupported language: {language}")

            if errors:
                found_errors = True
                lines = content_to_lint.splitlines()
                for error_line_num, error_message in errors:
                    if error_line_num < len(lines):
                        error_line = lines[error_line_num]
                        print(f"{error_message.replace('temp.py' if language == 'python' else 'temp.cpp', relative_path)}\n    {error_line}")
            else:
                print(f"✅ {relative_path}: no problems found.")
    return 1 if found_errors else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lint code blocks in Markdown files.')
    parser.add_argument('directory', nargs='?', default=os.getcwd(), help='The base directory to scan for Markdown files (default: current directory).')
    parser.add_argument('flake8_config', help='Path to the flake8 configuration file')
    parser.add_argument('language', choices=['python', 'cpp'], help='The programming language to lint')
    args = parser.parse_args()
    print(f"Scanning directory: {args.directory}")
    print(f"Using flake8 config: {args.flake8_config}")
    print(f"Linting language: {args.language}")
    exit_code = main(args.directory, args.flake8_config, args.language)
    print(f"Exit code: {exit_code}")
    sys.exit(exit_code)
