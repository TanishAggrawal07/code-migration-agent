using System;
using System.Collections.Generic;

namespace SchoolManagement.Models
{
    public class Student
    {
        public int Id { get; set; }
        public string FirstName { get; set; }
        public string LastName { get; set; }
        public string Email { get; set; }
        public DateTime DateOfBirth { get; set; }
        public double GPA { get; set; }
        public List<Course> EnrolledCourses { get; set; }

        public Student()
        {
            EnrolledCourses = new List<Course>();
        }

        public Student(int id, string firstName, string lastName, string email, DateTime dateOfBirth)
        {
            Id = id;
            FirstName = firstName;
            LastName = lastName;
            Email = email;
            DateOfBirth = dateOfBirth;
            GPA = 0.0;
            EnrolledCourses = new List<Course>();
        }

        public string GetFullName()
        {
            return $"{FirstName} {LastName}";
        }

        public int GetAge()
        {
            var today = DateTime.Today;
            int age = today.Year - DateOfBirth.Year;
            if (DateOfBirth.Date > today.AddYears(-age))
                age--;
            return age;
        }

        public bool IsHonorRoll()
        {
            return GPA >= 3.5;
        }

        public void EnrollInCourse(Course course)
        {
            if (course == null)
                throw new ArgumentException("Course cannot be null.");
            if (EnrolledCourses.Any(c => c.CourseId == course.CourseId))
                throw new InvalidOperationException("Student is already enrolled in this course.");
            EnrolledCourses.Add(course);
        }

        public override string ToString()
        {
            return $"Student[{Id}]: {GetFullName()}, GPA={GPA:F2}, Courses={EnrolledCourses.Count}";
        }
    }
}
