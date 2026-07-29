"""
Tests for JavaPostProcessor utility.
"""
from __future__ import annotations

import pytest
from app.utils.java_post_processor import (
    strip_comments_and_strings,
    parse_package_and_imports,
    extract_classes,
    split_members,
    parse_member_header,
    select_primary_class,
    clean_and_merge_java_source,
    compile_and_validate,
)

def test_strip_comments_and_strings():
    text = "public class Foo { // line comment\n /* block\n comment */\n String s = \"hello\"; char c = 'a'; }"
    clean = strip_comments_and_strings(text)
    
    assert len(clean) == len(text)
    # comments replaced with spaces
    assert "// line comment" not in clean
    assert "/* block\n comment */" not in clean
    # quotes preserved, but content replaced with space
    assert '"     "' in clean
    assert "' '" in clean


def test_parse_package_and_imports():
    text = """
    package com.test;
    // some comment
    import java.util.List;
    import org.springframework.stereotype.Service;
    import java.util.List; // duplicate
    """
    pkg, imports = parse_package_and_imports(text)
    assert pkg == "package com.test;"
    assert imports == [
        "import java.util.List;",
        "import org.springframework.stereotype.Service;"
    ]


def test_extract_classes():
    text = """
    @Service
    public class MyService implements IService {
        public void doWork() {}
    }
    class AnotherClass {}
    """
    classes = extract_classes(text)
    assert len(classes) == 2
    assert classes[0]["name"] == "MyService"
    assert "public class MyService implements IService" in classes[0]["header"]
    assert "@Service" in classes[0]["header"]
    assert "public void doWork() {}" in classes[0]["body"]
    assert classes[1]["name"] == "AnotherClass"


def test_split_members():
    body = """
    private int x = 10;
    public MyService() {
        this.x = 20;
    }
    public void execute() {
        System.out.println("Hello");
    }
    """
    members = split_members(body)
    # clean them
    members = [m.strip() for m in members if m.strip()]
    assert len(members) == 3
    assert members[0] == "private int x = 10;"
    assert "public MyService()" in members[1]
    assert "public void execute()" in members[2]


def test_parse_member_header():
    m1 = "public int add(int a, final List<String> list)"
    parsed1 = parse_member_header(m1, "Calculator")
    assert parsed1["type"] == "method"
    assert parsed1["name"] == "add"
    assert parsed1["signature"] == "add(int,List<String>)"
    
    m2 = "public Calculator(String name)"
    parsed2 = parse_member_header(m2, "Calculator")
    assert parsed2["type"] == "constructor"
    assert parsed2["name"] == "Calculator"
    assert parsed2["signature"] == "Calculator(String)"
    
    m3 = "private int value = 100;"
    parsed3 = parse_member_header(m3, "Calculator")
    assert parsed3["type"] == "field"

    m4 = "private final Map<Integer, String> emails = new HashMap<>();"
    parsed4 = parse_member_header(m4, "Calculator")
    assert parsed4["type"] == "field"

    m5 = "@GetMapping(\"/users\") public void getUsers()"
    parsed5 = parse_member_header(m5, "Calculator")
    assert parsed5["type"] == "method"
    assert parsed5["name"] == "getUsers"


def test_select_primary_class():
    c1 = {"name": "Calculator"}
    c2 = {"name": "CalculatorService"}
    c3 = {"name": "OtherService"}
    c4 = {"name": "Helper"}
    
    assert select_primary_class([c1, c2, c3, c4])["name"] == "CalculatorService"
    assert select_primary_class([c1, c3, c4])["name"] == "OtherService"
    assert select_primary_class([c1, c4])["name"] == "Calculator"
    assert select_primary_class([c4])["name"] == "Helper"


def test_clean_and_merge_java_source():
    text = """
    package com.example;
    import org.springframework.stereotype.Service;
    import java.util.List;
    
    @Service
    public class Calculator {
        private int val;
        // TODO: implement migration
        public void stubMethod() {}
        public int add(int a, int b) {
            return a + b;
        }
    }
    
    public class CalculatorService {
        private int val; // duplicate field
        public int subtract(int a, int b) {
            return a - b;
        }
        // AUTO-GENERATED STUB — Gemini unavailable
        public void brokenStub() {}
    }
    """
    
    merged = clean_and_merge_java_source(text)
    
    # Check that:
    # 1. Primary class is CalculatorService (CalculatorService > Calculator)
    assert "public class CalculatorService" in merged
    assert "public class Calculator {" not in merged
    
    # 2. Duplicate imports removed
    # 3. Duplicate classes removed
    # 4. Merged unique methods
    assert "public int add(int a, int b)" in merged
    assert "public int subtract(int a, int b)" in merged
    
    # 5. Stubs removed
    assert "stubMethod" not in merged
    assert "brokenStub" not in merged
    assert "AUTO-GENERATED STUB" not in merged
    assert "TODO" not in merged
    
    # 6. Package preserved
    assert "package com.example;" in merged
    # 7. Spring annotations preserved
    assert "@Service" in merged


def test_compile_and_validate():
    # A correct Spring Service class
    code = """
    package com.example;
    import org.springframework.stereotype.Service;
    import java.util.ArrayList;
    import java.util.List;
    
    @Service
    public class SimpleCalculator {
        private final List<String> ops = new ArrayList<>();
        public int add(int a, int b) {
            ops.add("add");
            return a + b;
        }
    }
    """
    
    success, errors = compile_and_validate(code, "SimpleCalculator", "test-run-001")
    assert success is True
    assert errors == ""
    
    # An incorrect class (syntax error)
    bad_code = """
    package com.example;
    public class BadOne {
        public int add(int a, int b) {
            return a + b // missing semicolon
        }
    }
    """
    bad_success, bad_errors = compile_and_validate(bad_code, "BadOne", "test-run-001")
    assert bad_success is False
    assert "error" in bad_errors


def test_case_insensitive_method_deduplication():
    text = """
    package com.example;
    public class Calculator {
        public int add(int a, int b) { return a + b; }
        public int Add(int a, int b) { return a + b; }
        public int Subtract(int a, int b) { return a - b; }
        public int subtract(int a, int b) { return a - b; }
    }
    """
    merged = clean_and_merge_java_source(text)
    
    # Assert standard camelCase version is kept and duplicates are removed
    assert "public int add(int a, int b)" in merged
    assert "public int Add(int a, int b)" not in merged
    assert "public int subtract(int a, int b)" in merged
    assert "public int Subtract(int a, int b)" not in merged

