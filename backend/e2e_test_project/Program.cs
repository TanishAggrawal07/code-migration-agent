using System;
using System.Collections.Generic;
using SchoolManagement.Models;
using SchoolManagement.Repositories;
using SchoolManagement.Services;

namespace SchoolManagement
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("=== School Management System ===");

            var repository = new StudentRepository();
            var service = new StudentService(repository);

            // Create courses
            var mathCourse = new Course(1, "Mathematics 101", "Introduction to Calculus", 3);
            var csCourse = new Course(2, "Computer Science 101", "Introduction to Programming", 4);
            var physicsCourse = new Course(3, "Physics 101", "Classical Mechanics", 3);

            // Create students
            var student1 = new Student(1, "Alice", "Johnson", "alice@school.edu", new DateTime(2000, 5, 15));
            student1.GPA = 3.8;

            var student2 = new Student(2, "Bob", "Smith", "bob@school.edu", new DateTime(1999, 11, 22));
            student2.GPA = 2.5;

            var student3 = new Student(3, "Carol", "Williams", "carol@school.edu", new DateTime(2001, 3, 8));
            student3.GPA = 3.9;

            // Register students
            service.RegisterStudent(student1);
            service.RegisterStudent(student2);
            service.RegisterStudent(student3);

            // Enroll students in courses
            service.EnrollStudentInCourse(1, mathCourse);
            service.EnrollStudentInCourse(1, csCourse);
            service.EnrollStudentInCourse(2, csCourse);
            service.EnrollStudentInCourse(3, mathCourse);
            service.EnrollStudentInCourse(3, physicsCourse);

            // Display all students
            Console.WriteLine("\n--- All Students ---");
            var allStudents = service.GetAllStudents();
            foreach (var s in allStudents)
            {
                Console.WriteLine(s.ToString());
            }

            // Display honor roll
            Console.WriteLine("\n--- Honor Roll ---");
            var honorStudents = service.GetHonorRollStudents();
            foreach (var s in honorStudents)
            {
                Console.WriteLine($"  {s.GetFullName()} — GPA: {s.GPA:F2}");
            }

            // Enrollment summary
            Console.WriteLine("\n--- Enrollment Summary ---");
            var summary = service.GetEnrollmentSummary();
            foreach (var entry in summary)
            {
                Console.WriteLine($"  {entry.Key}: {entry.Value}");
            }

            // Update GPA
            service.UpdateStudentGPA(2, 3.1);

            // GPA range query
            Console.WriteLine("\n--- Students with GPA 3.0-4.0 ---");
            var topStudents = service.GetStudentsByGPARange(3.0, 4.0);
            foreach (var s in topStudents)
            {
                Console.WriteLine($"  {s.GetFullName()} — GPA: {s.GPA:F2}");
            }

            Console.WriteLine($"\nTotal students: {service.GetTotalStudentCount()}");
            Console.WriteLine("=== Done ===");
        }
    }
}
