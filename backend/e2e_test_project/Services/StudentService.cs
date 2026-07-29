using System;
using System.Collections.Generic;
using SchoolManagement.Interfaces;
using SchoolManagement.Models;
using SchoolManagement.Utilities;

namespace SchoolManagement.Services
{
    public class StudentService
    {
        private readonly IStudentRepository _repository;
        private readonly ValidationHelper _validator;

        public StudentService(IStudentRepository repository)
        {
            _repository = repository ?? throw new ArgumentException("Repository cannot be null.");
            _validator = new ValidationHelper();
        }

        public Student GetStudent(int id)
        {
            return _repository.GetById(id);
        }

        public List<Student> GetAllStudents()
        {
            return _repository.GetAll();
        }

        public List<Student> GetHonorRollStudents()
        {
            return _repository.GetHonorStudents();
        }

        public List<Student> GetStudentsByGPARange(double min, double max)
        {
            if (min < 0.0 || max > 4.0 || min > max)
                throw new ArgumentException("Invalid GPA range. Must be between 0.0 and 4.0.");
            return _repository.GetByGPARange(min, max);
        }

        public void RegisterStudent(Student student)
        {
            if (student == null)
                throw new ArgumentException("Student cannot be null.");
            _validator.ValidateStudent(student);
            _repository.Add(student);
            Console.WriteLine($"Student registered: {student.GetFullName()}");
        }

        public void UpdateStudentGPA(int id, double newGPA)
        {
            if (newGPA < 0.0 || newGPA > 4.0)
                throw new ArgumentException($"Invalid GPA value: {newGPA}. Must be between 0.0 and 4.0.");
            var student = _repository.GetById(id);
            student.GPA = newGPA;
            _repository.Update(student);
            Console.WriteLine($"Updated GPA for {student.GetFullName()} to {newGPA:F2}");
        }

        public void RemoveStudent(int id)
        {
            var student = _repository.GetById(id);
            _repository.Delete(id);
            Console.WriteLine($"Removed student: {student.GetFullName()}");
        }

        public void EnrollStudentInCourse(int studentId, Course course)
        {
            var student = _repository.GetById(studentId);
            student.EnrollInCourse(course);
            _repository.Update(student);
            Console.WriteLine($"Enrolled {student.GetFullName()} in {course.CourseName}");
        }

        public int GetTotalStudentCount()
        {
            return _repository.Count();
        }

        public Dictionary<string, int> GetEnrollmentSummary()
        {
            var students = _repository.GetAll();
            var summary = new Dictionary<string, int>();
            summary["total"] = students.Count;
            summary["honorRoll"] = students.Count(s => s.IsHonorRoll());
            summary["atRisk"] = students.Count(s => s.GPA < 2.0);
            return summary;
        }
    }
}
