using System.Collections.Generic;
using SchoolManagement.Models;

namespace SchoolManagement.Interfaces
{
    public interface IStudentRepository
    {
        Student GetById(int id);
        List<Student> GetAll();
        List<Student> GetByGPARange(double minGPA, double maxGPA);
        List<Student> GetHonorStudents();
        void Add(Student student);
        void Update(Student student);
        void Delete(int id);
        bool Exists(int id);
        int Count();
    }
}
