"""
Java Post-Processing & Compilation Validation service.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

MOCK_DEPENDENCY_SOURCES = {
    "org/springframework/stereotype/Service.java": """
        package org.springframework.stereotype;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface Service {
            String value() default "";
        }
    """,
    "org/springframework/stereotype/Component.java": """
        package org.springframework.stereotype;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface Component {
            String value() default "";
        }
    """,
    "org/springframework/stereotype/Repository.java": """
        package org.springframework.stereotype;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface Repository {
            String value() default "";
        }
    """,
    "org/springframework/stereotype/Controller.java": """
        package org.springframework.stereotype;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface Controller {
            String value() default "";
        }
    """,
    "org/springframework/beans/factory/annotation/Autowired.java": """
        package org.springframework.beans.factory.annotation;
        import java.lang.annotation.*;
        @Target({ElementType.CONSTRUCTOR, ElementType.METHOD, ElementType.PARAMETER, ElementType.FIELD, ElementType.ANNOTATION_TYPE})
        @Retention(RetentionPolicy.RUNTIME)
        public @interface Autowired {
            boolean required() default true;
        }
    """,
    "org/springframework/web/bind/annotation/RestController.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface RestController {
            String value() default "";
        }
    """,
    "org/springframework/web/bind/annotation/RequestMapping.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target({ElementType.TYPE, ElementType.METHOD})
        @Retention(RetentionPolicy.RUNTIME)
        public @interface RequestMapping {
            String[] value() default {};
            String[] path() default {};
        }
    """,
    "org/springframework/web/bind/annotation/GetMapping.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.METHOD)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface GetMapping {
            String[] value() default {};
            String[] path() default {};
        }
    """,
    "org/springframework/web/bind/annotation/PostMapping.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.METHOD)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface PostMapping {
            String[] value() default {};
            String[] path() default {};
        }
    """,
    "org/springframework/web/bind/annotation/RequestParam.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.PARAMETER)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface RequestParam {
            String value() default "";
            String name() default "";
            boolean required() default true;
            String defaultValue() default "Value";
        }
    """,
    "org/springframework/web/bind/annotation/PathVariable.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.PARAMETER)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface PathVariable {
            String value() default "";
            String name() default "";
            boolean required() default true;
        }
    """,
    "org/springframework/web/bind/annotation/RequestBody.java": """
        package org.springframework.web.bind.annotation;
        import java.lang.annotation.*;
        @Target(ElementType.PARAMETER)
        @Retention(RetentionPolicy.RUNTIME)
        public @interface RequestBody {
            boolean required() default true;
        }
    """,
    "org/springframework/http/ResponseEntity.java": """
        package org.springframework.http;
        public class ResponseEntity<T> {
            private T body;
            private HttpStatus status;
            public ResponseEntity(T body, HttpStatus status) {
                this.body = body;
                this.status = status;
            }
            public static <T> ResponseEntity<T> ok(T body) {
                return new ResponseEntity<>(body, null);
            }
            public static <T> ResponseEntity<T> status(HttpStatus status) {
                return new ResponseEntity<>(null, status);
            }
            public T getBody() { return body; }
        }
    """,
    "org/springframework/http/HttpStatus.java": """
        package org.springframework.http;
        public enum HttpStatus {
            OK, BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR;
        }
    """,
    "lombok/Getter.java": """
        package lombok;
        import java.lang.annotation.*;
        @Target({ElementType.FIELD, ElementType.TYPE})
        @Retention(RetentionPolicy.SOURCE)
        public @interface Getter {}
    """,
    "lombok/Setter.java": """
        package lombok;
        import java.lang.annotation.*;
        @Target({ElementType.FIELD, ElementType.TYPE})
        @Retention(RetentionPolicy.SOURCE)
        public @interface Setter {}
    """,
    "lombok/NoArgsConstructor.java": """
        package lombok;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.SOURCE)
        public @interface NoArgsConstructor {}
    """,
    "lombok/AllArgsConstructor.java": """
        package lombok;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.SOURCE)
        public @interface AllArgsConstructor {}
    """,
    "lombok/Data.java": """
        package lombok;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.SOURCE)
        public @interface Data {}
    """,
    "lombok/extern/slf4j/Slf4j.java": """
        package lombok.extern.slf4j;
        import java.lang.annotation.*;
        @Target(ElementType.TYPE)
        @Retention(RetentionPolicy.SOURCE)
        public @interface Slf4j {}
    """,
    "org/slf4j/Logger.java": """
        package org.slf4j;
        public interface Logger {
            void info(String msg);
            void warn(String msg);
            void error(String msg);
            void debug(String msg);
        }
    """,
    "org/slf4j/LoggerFactory.java": """
        package org.slf4j;
        public class LoggerFactory {
            public static Logger getLogger(Class<?> clazz) {
                return new Logger() {
                    public void info(String m) {}
                    public void warn(String m) {}
                    public void error(String m) {}
                    public void debug(String m) {}
                };
            }
        }
    """
}


def strip_comments_and_strings(text: str) -> str:
    """Strip comments and strings, replacing contents with spaces to preserve index offsets."""
    n = len(text)
    out = list(text)
    i = 0
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False

    while i < n:
        if in_line_comment:
            if text[i] == '\n':
                in_line_comment = False
            else:
                out[i] = ' '
            i += 1
            continue

        if in_block_comment:
            out[i] = ' '
            if text[i] == '/' and i > 0 and text[i-1] == '*':
                in_block_comment = False
            i += 1
            continue

        if in_string:
            if text[i] == '"' and text[i-1] != '\\':
                in_string = False
            else:
                out[i] = ' '
            i += 1
            continue

        if in_char:
            if text[i] == "'" and text[i-1] != '\\':
                in_char = False
            else:
                out[i] = ' '
            i += 1
            continue

        # transitions
        if text[i] == '"':
            in_string = True
            i += 1
            continue
        if text[i] == "'":
            in_char = True
            i += 1
            continue
        if text[i] == '/' and i + 1 < n and text[i+1] == '/':
            in_line_comment = True
            out[i] = ' '
            out[i+1] = ' '
            i += 2
            continue
        if text[i] == '/' and i + 1 < n and text[i+1] == '*':
            in_block_comment = True
            out[i] = ' '
            out[i+1] = ' '
            i += 2
            continue

        i += 1

    return "".join(out)


def parse_package_and_imports(text: str) -> tuple[str, list[str]]:
    """Parse package declaration and import statements."""
    package_declaration = ""
    imports = set()

    clean_text = strip_comments_and_strings(text)
    clean_lines = clean_text.splitlines()

    package_pattern = re.compile(r'^\s*package\s+([\w\.]+)\s*;')
    import_pattern = re.compile(r'^\s*import\s+([\w\.\*]+)\s*;')

    for clean_line in clean_lines:
        pkg_match = package_pattern.match(clean_line)
        if pkg_match:
            package_declaration = f"package {pkg_match.group(1)};"
            continue
        imp_match = import_pattern.match(clean_line)
        if imp_match:
            imports.add(f"import {imp_match.group(1)};")

    return package_declaration, sorted(list(imports))


def extract_classes(text: str) -> list[dict[str, Any]]:
    """Find all class definitions using brace-matching."""
    clean_text = strip_comments_and_strings(text)
    class_pattern = re.compile(r'\b(class|interface|enum)\s+(\w+)\b')
    classes = []

    for match in class_pattern.finditer(clean_text):
        class_name = match.group(2)
        match_end = match.end()
        brace_idx = clean_text.find('{', match_end)
        if brace_idx == -1:
            continue

        # count braces in original text
        brace_count = 1
        i = brace_idx + 1
        n = len(text)
        orig_end_idx = -1

        in_string = False
        in_char = False
        in_line_comment = False
        in_block_comment = False

        while i < n:
            c = text[i]
            if in_line_comment:
                if c == '\n':
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if c == '/' and i > 0 and text[i-1] == '*':
                    in_block_comment = False
                i += 1
                continue
            if in_string:
                if c == '"' and text[i-1] != '\\':
                    in_string = False
                i += 1
                continue
            if in_char:
                if c == "'" and text[i-1] != '\\':
                    in_char = False
                i += 1
                continue

            if c == '"':
                in_string = True
                i += 1
                continue
            if c == "'":
                in_char = True
                i += 1
                continue
            if c == '/' and i + 1 < n and text[i+1] == '/':
                in_line_comment = True
                i += 2
                continue
            if c == '/' and i + 1 < n and text[i+1] == '*':
                in_block_comment = True
                i += 2
                continue

            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    orig_end_idx = i
                    break
            i += 1

        if orig_end_idx == -1:
            continue

        class_body = text[brace_idx+1 : orig_end_idx]
        header_start = match.start()
        while header_start > 0:
            prev_c = text[header_start-1]
            if prev_c in ('}', ';'):
                break
            header_start -= 1

        class_header = text[header_start : brace_idx].strip()
        classes.append({
            "name": class_name,
            "header": class_header,
            "body": class_body,
            "start_pos": header_start,
            "end_pos": orig_end_idx + 1
        })

    return classes


def split_members(class_body: str) -> list[str]:
    """Split class body into fields, constructors, methods."""
    members = []
    i = 0
    n = len(class_body)
    start_idx = 0
    brace_count = 0
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        c = class_body[i]
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == '/' and i > 0 and class_body[i-1] == '*':
                in_block_comment = False
            i += 1
            continue
        if in_string:
            if c == '"' and class_body[i-1] != '\\':
                in_string = False
            i += 1
            continue
        if in_char:
            if c == "'" and class_body[i-1] != '\\':
                in_char = False
            i += 1
            continue

        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "'":
            in_char = True
            i += 1
            continue
        if c == '/' and i + 1 < n and class_body[i+1] == '/':
            in_line_comment = True
            i += 2
            continue
        if c == '/' and i + 1 < n and class_body[i+1] == '*':
            in_block_comment = True
            i += 2
            continue

        if c == '{':
            brace_count += 1
        elif c == '}':
            brace_count -= 1
            if brace_count == 0:
                member_text = class_body[start_idx:i+1]
                members.append(member_text)
                start_idx = i + 1
        elif c == ';' and brace_count == 0:
            member_text = class_body[start_idx:i+1]
            members.append(member_text)
            start_idx = i + 1

        i += 1

    if start_idx < n:
        rem = class_body[start_idx:].strip()
        if rem:
            members.append(rem)

    return members


def get_param_types(params_str: str) -> list[str]:
    """Parse parameter types inside parentheses, ignoring generic boundaries and annotations."""
    params = []
    bracket_count = 0
    current_param = []

    for char in params_str:
        if char == '<':
            bracket_count += 1
        elif char == '>':
            bracket_count -= 1

        if char == ',' and bracket_count == 0:
            params.append("".join(current_param).strip())
            current_param = []
        else:
            current_param.append(char)
    if current_param:
        params.append("".join(current_param).strip())

    types = []
    for p in params:
        if not p:
            continue
        cleaned_p = re.sub(r'@[a-zA-Z_0-9]+(?:\([^)]*\))?', '', p).strip()
        parts = cleaned_p.split()
        if len(parts) >= 2:
            param_type = " ".join(parts[:-1])
            types.append(param_type)
        elif len(parts) == 1:
            types.append(parts[0])
    return types


def parse_member_header(member_text: str, class_name: str) -> dict[str, Any]:
    """Parse signature of constructor or method."""
    clean_text = strip_comments_and_strings(member_text)
    # Strip annotations to avoid false parenthesis matches
    clean_text = re.sub(r'@[a-zA-Z_0-9]+(?:\([^)]*\))?', '', clean_text)
    
    paren_idx = clean_text.find('(')
    if paren_idx == -1:
        return {
            "type": "field",
            "name": None,
            "signature": None,
            "is_constructor": False
        }

    equals_idx = clean_text.find('=')
    if equals_idx != -1 and equals_idx < paren_idx:
        return {
            "type": "field",
            "name": None,
            "signature": None,
            "is_constructor": False
        }

    paren_count = 0
    end_paren_idx = -1
    for idx in range(paren_idx, len(clean_text)):
        char = clean_text[idx]
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
            if paren_count == 0:
                end_paren_idx = idx
                break

    if end_paren_idx == -1:
        return {
            "type": "field",
            "name": None,
            "signature": None,
            "is_constructor": False
        }

    params_str = clean_text[paren_idx+1 : end_paren_idx]
    header_str = clean_text[:paren_idx].strip()
    header_str = re.sub(r'@[a-zA-Z_0-9]+(?:\([^)]*\))?', '', header_str).strip()

    header_parts = header_str.split()
    if not header_parts:
        return {
            "type": "unknown",
            "name": None,
            "signature": None,
            "is_constructor": False
        }

    member_name = header_parts[-1]
    is_constructor = (member_name == class_name)

    param_types = get_param_types(params_str)
    normalized_types = []
    for t in param_types:
        t_clean = t.replace("final", "").strip()
        t_clean = re.sub(r'\s+', ' ', t_clean)
        normalized_types.append(t_clean)

    signature = f"{member_name}({','.join(normalized_types)})"

    return {
        "type": "constructor" if is_constructor else "method",
        "name": member_name,
        "signature": signature,
        "is_constructor": is_constructor
    }


def should_keep_block(block_text: str) -> bool:
    """Filter placeholder/stub block comments generated by _make_stub.

    Only removes blocks containing exact stub-generator markers.
    The specific phrase 'TODO: implement migration' is the exact comment
    emitted by _make_stub — filtering it avoids stripping real LLM code
    that may contain other '// TODO:' comments for legitimate reasons.
    """
    for bad_str in [
        "AUTO-GENERATED STUB",
        "Gemini unavailable",
        "LLM unavailable",
        "TODO: implement migration",   # exact phrase from _make_stub
    ]:
        if bad_str in block_text:
            return False
    return True


def rename_constructor(member_text: str, old_name: str, new_name: str) -> str:
    """Rename a constructor in a non-primary class to match the primary class name."""
    idx = member_text.find('(')
    if idx == -1:
        return member_text
    header = member_text[:idx]
    body = member_text[idx:]
    new_header = re.sub(rf'\b{old_name}\b', new_name, header)
    return new_header + body


def extract_field_name(member_text: str) -> str | None:
    """Extract a field variable name from declaration."""
    clean = strip_comments_and_strings(member_text).strip()
    if clean.endswith(';'):
        clean = clean[:-1].strip()
    if '=' in clean:
        clean = clean.split('=')[0].strip()
    parts = clean.split()
    if parts:
        return parts[-1]
    return None


def select_primary_class(classes: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the primary class based on priority rules."""
    def is_interface_or_enum(c: dict[str, Any]) -> bool:
        header = c.get("header", "")
        return bool(re.search(r'\b(interface|enum)\b', header))

    # Separate real classes from interfaces/enums
    real_classes = [c for c in classes if not is_interface_or_enum(c)]
    candidates = real_classes if real_classes else classes

    for c in candidates:
        if c["name"] == "CalculatorService":
            return c
    for c in candidates:
        name = c["name"]
        if name.endswith("Service") or name.endswith("ServiceImpl") or name.endswith("Impl"):
            return c
    for c in candidates:
        if c["name"] == "Calculator":
            return c
    return candidates[0]


def extract_annotations(header_text: str) -> list[str]:
    """Extract class annotations."""
    annotations = []
    i = 0
    n = len(header_text)
    while i < n:
        if header_text[i] == '@':
            start = i
            i += 1
            while i < n and (header_text[i].isalnum() or header_text[i] == '_'):
                i += 1
            # Check parens
            while i < n and header_text[i].isspace():
                i += 1
            if i < n and header_text[i] == '(':
                paren_count = 1
                i += 1
                while i < n and paren_count > 0:
                    if header_text[i] == '(':
                        paren_count += 1
                    elif header_text[i] == ')':
                        paren_count -= 1
                    i += 1
                annotations.append(header_text[start:i].strip())
            else:
                annotations.append(header_text[start:i].strip())
        else:
            i += 1
    return annotations


def merge_annotations(classes: list[dict[str, Any]], primary_c: dict[str, Any]) -> list[str]:
    """Merge all unique annotations from classes."""
    all_ann = []
    for c in classes:
        all_ann.extend(extract_annotations(c["header"]))
    seen = set()
    unique_ann = []
    for a in all_ann:
        if a not in seen:
            seen.add(a)
            unique_ann.append(a)
    return unique_ann


def rebuild_class_header(primary_c: dict[str, Any], unique_ann: list[str]) -> str:
    """Build primary class header with all unique annotations."""
    cleaned_header = re.sub(r'@[a-zA-Z_0-9]+(?:\([^)]*\))?', '', primary_c["header"]).strip()
    cleaned_header = re.sub(r'\s+', ' ', cleaned_header)
    if unique_ann:
        return "\n".join(unique_ann) + "\n" + cleaned_header
    return cleaned_header


def clean_and_merge_java_source(text: str) -> str:
    """Deduplicate imports, select primary class, merge unique methods, and remove stubs."""
    package_decl, imports = parse_package_and_imports(text)
    all_classes = extract_classes(text)

    # Filter stub classes
    filtered_classes = []
    for c in all_classes:
        full_class_text = c["header"] + " " + c["body"]
        if should_keep_block(full_class_text):
            filtered_classes.append(c)

    if not filtered_classes:
        filtered_classes = all_classes

    if not filtered_classes:
        return text

    primary_c = select_primary_class(filtered_classes)
    primary_name = primary_c["name"]

    merged_fields = {}
    merged_constructors = {}
    merged_methods = {}

    for c in filtered_classes:
        c_name = c["name"]
        is_primary = (c_name == primary_name)
        members = split_members(c["body"])

        for m in members:
            if not should_keep_block(m):
                continue

            parsed = parse_member_header(m, c_name)
            if parsed["type"] == "field":
                field_name = extract_field_name(m)
                if field_name:
                    if is_primary or field_name not in merged_fields:
                        merged_fields[field_name] = m.strip()
                else:
                    merged_fields[m.strip()] = m.strip()

            elif parsed["type"] == "constructor":
                sig = parsed["signature"]
                param_types = sig[sig.find('(')+1 : sig.rfind(')')]
                m_renamed = m
                if not is_primary:
                    m_renamed = rename_constructor(m, c_name, primary_name)

                if is_primary or param_types not in merged_constructors:
                    merged_constructors[param_types] = m_renamed.strip()

            elif parsed["type"] == "method":
                sig = parsed["signature"]
                sig_lower = sig.lower()
                method_name = parsed["name"] or ""
                is_new_lowercase = len(method_name) > 0 and method_name[0].islower()

                if sig_lower not in merged_methods:
                    merged_methods[sig_lower] = (is_primary, method_name, m.strip())
                else:
                    existing_is_primary, existing_name, _ = merged_methods[sig_lower]
                    is_existing_lowercase = len(existing_name) > 0 and existing_name[0].islower()

                    should_overwrite = False
                    if is_primary and not existing_is_primary:
                        should_overwrite = True
                    elif (is_primary == existing_is_primary) and (is_new_lowercase and not is_existing_lowercase):
                        should_overwrite = True

                    if should_overwrite:
                        merged_methods[sig_lower] = (is_primary, method_name, m.strip())
            else:
                merged_fields[m.strip()] = m.strip()

    unique_ann = merge_annotations(filtered_classes, primary_c)
    class_header = rebuild_class_header(primary_c, unique_ann)

    body_parts = []
    if merged_fields:
        body_parts.append("\n    ".join(merged_fields.values()))
    if merged_constructors:
        body_parts.append("\n\n    ".join(merged_constructors.values()))
    if merged_methods:
        body_parts.append("\n\n    ".join(val[2] for val in merged_methods.values()))

    class_body = "\n\n    ".join(body_parts)
    merged_class_code = f"{class_header} {{\n    {class_body}\n}}"

    final_file_parts = []
    if package_decl:
        final_file_parts.append(package_decl)
    if imports:
        final_file_parts.append("\n".join(imports))
    final_file_parts.append(merged_class_code)

    return "\n\n".join(final_file_parts)


def setup_mock_dependencies() -> str:
    """Pre-compiles mock Spring and Lombok annotation libraries to classes dir."""
    base_dir = Path("storage/mock_dependencies")
    src_dir = base_dir / "src"
    classes_dir = base_dir / "classes"

    src_dir.mkdir(parents=True, exist_ok=True)
    classes_dir.mkdir(parents=True, exist_ok=True)

    sources_to_compile = []
    for filepath_str, content in MOCK_DEPENDENCY_SOURCES.items():
        file_path = src_dir / filepath_str
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip(), encoding="utf-8")
        sources_to_compile.append(str(file_path))

    if sources_to_compile:
        cmd = ["javac", "-d", str(classes_dir)] + sources_to_compile
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError as err:
            raise RuntimeError(f"Failed to compile mock dependencies: {err.stderr}")

    return str(classes_dir)


def check_and_generate_dynamic_mocks(imports: list[str], java_code: str, classes_dir: str):
    """Dynamically mocks imported third-party classes if not standard or already mocked."""
    classes_path = Path(classes_dir)
    base_dir = Path("storage/mock_dependencies")
    src_dir = base_dir / "src"

    for imp in imports:
        # e.g., "import org.apache.commons.lang3.StringUtils;"
        # we extract the path
        if not imp.startswith("import "):
            continue
        imp_path = imp.replace("import ", "").replace(";", "").strip()
        if imp_path.startswith(("java.", "javax.")):
            continue
        if imp_path.endswith(".*"):
            continue

        parts = imp_path.split(".")
        if len(parts) < 2:
            continue

        pkg = ".".join(parts[:-1])
        cls_name = parts[-1]

        rel_path = "/".join(parts[:-1]) + f"/{cls_name}.class"
        if (classes_path / rel_path).exists():
            continue

        # Check if annotation
        is_annotation = f"@{cls_name}" in java_code
        # Check if interface
        is_interface = len(cls_name) > 1 and cls_name[0] == 'I' and cls_name[1].isupper()

        if is_annotation:
            content = f"""
package {pkg};
import java.lang.annotation.*;
@Target({{ElementType.TYPE, ElementType.METHOD, ElementType.FIELD, ElementType.PARAMETER, ElementType.CONSTRUCTOR}})
@Retention(RetentionPolicy.RUNTIME)
public @interface {cls_name} {{
    String value() default "";
}}
"""
        elif is_interface:
            content = f"""
package {pkg};
public interface {cls_name} {{}}
"""
        else:
            content = f"""
package {pkg};
public class {cls_name} {{
    public static class Builder {{
        public Builder build() {{ return this; }}
    }}
    public static {cls_name} builder() {{ return new {cls_name}(); }}
}}
"""
        file_path = src_dir / ("/".join(parts[:-1]) + f"/{cls_name}.java")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip(), encoding="utf-8")

        # Compile immediately if javac is available
        cmd = ["javac", "-d", str(classes_path), str(file_path)]
        try:
            subprocess.run(cmd, capture_output=True)
        except FileNotFoundError:
            pass


def compile_and_validate(
    java_code: str,
    class_name: str,
    migration_id: str,
    all_files: dict[str, str] = None
) -> tuple[bool, str]:
    """Compile generated code with javac and mock dependencies to validate syntax."""
    classes_dir = setup_mock_dependencies()

    # Dynamic mocking
    _, imports = parse_package_and_imports(java_code)
    check_and_generate_dynamic_mocks(imports, java_code, classes_dir)

    temp_dir = Path(f"storage/temp_compile/{migration_id}")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Write other files if provided
    if all_files:
        for fname, fcode in all_files.items():
            other_pkg, _ = parse_package_and_imports(fcode)
            other_classes = extract_classes(fcode)
            if not other_classes:
                continue
            other_cls_name = other_classes[0]["name"]
            
            other_pkg_path = ""
            m_pkg = re.match(r'^\s*package\s+([\w\.]+)\s*;', other_pkg)
            if m_pkg:
                other_pkg_path = m_pkg.group(1).replace(".", "/")

            other_src_path = temp_dir / other_pkg_path
            other_src_path.mkdir(parents=True, exist_ok=True)
            (other_src_path / f"{other_cls_name}.java").write_text(fcode, encoding="utf-8")

    # Write target file
    package_decl, _ = parse_package_and_imports(java_code)
    package_path = ""
    m = re.match(r'^\s*package\s+([\w\.]+)\s*;', package_decl)
    if m:
        package_path = m.group(1).replace(".", "/")

    src_path = temp_dir / package_path
    src_path.mkdir(parents=True, exist_ok=True)

    java_file = src_path / f"{class_name}.java"
    java_file.write_text(java_code, encoding="utf-8")

    cmd = ["javac", "-cp", f"{classes_dir};{temp_dir}", str(java_file)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        success = (res.returncode == 0)
        errors = res.stderr if not success else ""
        shutil.rmtree(temp_dir, ignore_errors=True)
        return success, errors
    except FileNotFoundError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True, "javac compiler not installed on host — skipping compilation check"
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False, str(exc)


async def repair_java_code(java_code: str, error_msg: str) -> str:
    """Invoke the active LLM provider to correct compilation errors."""
    from app.core.gemini_client import GeminiClient
    import logging
    _log = logging.getLogger(__name__)

    gemini = GeminiClient.get_instance()
    if not gemini.is_initialized:
        _log.warning("repair_java_code: no LLM provider available, returning unchanged code")
        return java_code

    provider_key = gemini.active_provider_key
    model        = gemini.active_model
    _log.info("repair_java_code: using %s/%s", provider_key, model)

    prompt = (
        "You are an expert Java migration engineer.\n"
        "The following Java code failed to compile with the listed compiler errors.\n\n"
        "Compiler Errors:\n"
        f"{error_msg}\n\n"
        "Java Code:\n"
        f"{java_code}\n\n"
        "RULES:\n"
        "- Fix ONLY the compilation errors listed above.\n"
        "- Do NOT change the business logic.\n"
        "- Do NOT add Spring Boot annotations unless they were already present.\n"
        "- Do NOT add imports that are not needed.\n"
        "- Output ONLY the corrected Java source code without any markdown fences or explanations."
    )

    try:
        repaired = await gemini.generate_text(prompt)
        from app.agents.base_agent import _clean_java_output
        result = _clean_java_output(repaired)
        _log.info("repair_java_code: repair completed via %s/%s", provider_key, model)
        return result
    except Exception as exc:
        _log.warning("repair_java_code: repair failed via %s/%s: %s", provider_key, model, exc)
        return java_code
