using System;
using System.Text.RegularExpressions;
using SchoolManagement.Models;

namespace SchoolManagement.Utilities
{
    public class ValidationHelper
    {
        private static readonly Regex EmailRegex = new Regex(
            @"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            RegexOptions.Compiled
        );

        public void ValidateStudent(Student student)
        {
            if (student == null)
                throw new ArgumentException("Student cannot be null.");
            if (string.IsNullOrWhiteSpace(student.FirstName))
                throw new ArgumentException("First name is required.");
            if (string.IsNullOrWhiteSpace(student.LastName))
                throw new ArgumentException("Last name is required.");
            if (!IsValidEmail(student.Email))
                throw new ArgumentException($"Invalid email address: {student.Email}");
            if (student.Id <= 0)
                throw new ArgumentException("Student ID must be a positive integer.");
        }

        public bool IsValidEmail(string email)
        {
            if (string.IsNullOrWhiteSpace(email))
                return false;
            return EmailRegex.IsMatch(email);
        }

        public bool IsValidGPA(double gpa)
        {
            return gpa >= 0.0 && gpa <= 4.0;
        }

        public string FormatGPA(double gpa)
        {
            return gpa.ToString("F2");
        }

        public bool IsAdult(DateTime dateOfBirth)
        {
            var today = DateTime.Today;
            int age = today.Year - dateOfBirth.Year;
            if (dateOfBirth.Date > today.AddYears(-age))
                age--;
            return age >= 18;
        }
    }
}
