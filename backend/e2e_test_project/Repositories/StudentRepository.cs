using System;
using System.Collections.Generic;
using System.Linq;
using SchoolManagement.Interfaces;
using SchoolManagement.Models;

namespace SchoolManagement.Repositories
{
    public class StudentRepository : IStudentRepository
    {
        private readonly Dictionary<int, Student> _store;

        public StudentRepository()
        {
            _store = new Dictionary<int, Student>();
        }

        public Student GetById(int id)
        {
            if (!_store.ContainsKey(id))
                throw new KeyNotFoundException($"Student with id {id} not found.");
            return _store[id];
        }

        public List<Student> GetAll()
        {
            return _store.Values.OrderBy(s => s.LastName).ThenBy(s => s.FirstName).ToList();
        }

        public List<Student> GetByGPARange(double minGPA, double maxGPA)
        {
            return _store.Values
                .Where(s => s.GPA >= minGPA && s.GPA <= maxGPA)
                .OrderByDescending(s => s.GPA)
                .ToList();
        }

        public List<Student> GetHonorStudents()
        {
            return _store.Values.Where(s => s.IsHonorRoll()).ToList();
        }

        public void Add(Student student)
        {
            if (student == null)
                throw new ArgumentException("Student cannot be null.");
            if (_store.ContainsKey(student.Id))
                throw new InvalidOperationException($"Student with id {student.Id} already exists.");
            _store[student.Id] = student;
        }

        public void Update(Student student)
        {
            if (student == null)
                throw new ArgumentException("Student cannot be null.");
            if (!_store.ContainsKey(student.Id))
                throw new KeyNotFoundException($"Student with id {student.Id} not found.");
            _store[student.Id] = student;
        }

        public void Delete(int id)
        {
            if (!_store.ContainsKey(id))
                throw new KeyNotFoundException($"Student with id {id} not found.");
            _store.Remove(id);
        }

        public bool Exists(int id)
        {
            return _store.ContainsKey(id);
        }

        public int Count()
        {
            return _store.Count;
        }
    }
}
