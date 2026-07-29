using System;
using System.Collections.Generic;

namespace SchoolManagement.Models
{
    public class Teacher
    {
        public int Id { get; set; }
        public string FirstName { get; set; }
        public string LastName { get; set; }
        public string Email { get; set; }
        public string Department { get; set; }
        public decimal Salary { get; set; }
        public List<Course> TeachingCourses { get; set; }

        public Teacher()
        {
            TeachingCourses = new List<Course>();
        }

        public Teacher(int id, string firstName, string lastName, string email, string department, decimal salary)
        {
            Id = id;
            FirstName = firstName;
            LastName = lastName;
            Email = email;
            Department = department;
            Salary = salary;
            TeachingCourses = new List<Course>();
        }

        public string GetFullName()
        {
            return $"{FirstName} {LastName}";
        }

        public void AssignCourse(Course course)
        {
            if (course == null)
                throw new ArgumentException("Course cannot be null.");
            TeachingCourses.Add(course);
            course.Teacher = this;
        }

        public decimal GetAnnualSalary()
        {
            return Salary * 12;
        }

        public List<Course> GetActiveCourses()
        {
            return TeachingCourses.Where(c => c.IsActive).ToList();
        }

        public override string ToString()
        {
            return $"Teacher[{Id}]: {GetFullName()}, Dept={Department}, Courses={TeachingCourses.Count}";
        }
    }
}
