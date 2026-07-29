using System;
using System.Collections.Generic;

namespace SchoolManagement.Models
{
    public class Course
    {
        public int CourseId { get; set; }
        public string CourseName { get; set; }
        public string Description { get; set; }
        public int Credits { get; set; }
        public bool IsActive { get; set; }
        public Teacher Teacher { get; set; }
        public List<Student> EnrolledStudents { get; set; }

        public Course()
        {
            EnrolledStudents = new List<Student>();
            IsActive = true;
        }

        public Course(int courseId, string courseName, string description, int credits)
        {
            CourseId = courseId;
            CourseName = courseName;
            Description = description;
            Credits = credits;
            IsActive = true;
            EnrolledStudents = new List<Student>();
        }

        public int GetEnrollmentCount()
        {
            return EnrolledStudents.Count;
        }

        public double GetAverageGPA()
        {
            if (!EnrolledStudents.Any())
                return 0.0;
            return EnrolledStudents.Average(s => s.GPA);
        }

        public List<Student> GetHonorStudents()
        {
            return EnrolledStudents.Where(s => s.IsHonorRoll()).ToList();
        }

        public void DeactivateCourse()
        {
            IsActive = false;
        }

        public override string ToString()
        {
            return $"Course[{CourseId}]: {CourseName} ({Credits} credits), Active={IsActive}, Students={EnrolledStudents.Count}";
        }
    }
}
