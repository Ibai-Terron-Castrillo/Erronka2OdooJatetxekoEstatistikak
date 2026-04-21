using Microsoft.AspNetCore.Mvc;
using Xunit;
using Moq;
using JatetxeaApi.Controllerrak;
using JatetxeaApi.Modeloak;
using JatetxeaApi.Repositorioak;
using JatetxeaApi.DTOak;
using System.Collections.Generic;
using System.Linq;

namespace JatetxeaApi.Testak
{
    public class MahaiakControllerTests
    {
        [Fact]
        public void GetAll_OkItzultzenDu_MahaiakExistitzenDirenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            var mahaiak = new List<Mahaiak>
            {
                new Mahaiak { Id = 1, MahaiaZbk = 1, Edukiera = 4, Egoera = "Libre" },
                new Mahaiak { Id = 2, MahaiaZbk = 2, Edukiera = 6, Egoera = "Okupatuta" }
            };
            mockRepo.Setup(r => r.GetAll()).Returns(mahaiak);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.GetAll();

            var okResult = Assert.IsType<OkObjectResult>(result);
            var dtoList = Assert.IsAssignableFrom<IEnumerable<MahaiakDto>>(okResult.Value);
            Assert.Equal(2, dtoList.Count());
        }

        [Fact]
        public void Get_OkItzultzenDu_MahaiaExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            var mahaia = new Mahaiak { Id = 5, MahaiaZbk = 5, Edukiera = 4, Egoera = "Libre" };
            mockRepo.Setup(r => r.Get(5)).Returns(mahaia);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Get(5);

            var okResult = Assert.IsType<OkObjectResult>(result);
            var dto = Assert.IsType<MahaiakDto>(okResult.Value);
            Assert.Equal(5, dto.Id);
            Assert.Equal(5, dto.MahaiaZbk);
        }

        [Fact]
        public void Get_NotFoundItzultzenDu_MahaiaEzExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            mockRepo.Setup(r => r.Get(999)).Returns((Mahaiak)null);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Get(999);

            var notFound = Assert.IsType<NotFoundObjectResult>(result);
            dynamic value = notFound.Value;
            Assert.Equal("Ez da aurkitu", value.mezua);
        }

        [Fact]
        public void Sortu_OkItzultzenDu_MahaiaOndoSortzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            var dto = new MahaiakSortuDto { MahaiaZbk = 10, Edukiera = 4, Egoera = "Libre" };
            Mahaiak savedMahaia = null;
            mockRepo.Setup(r => r.Add(It.IsAny<Mahaiak>())).Callback<Mahaiak>(m => savedMahaia = m);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Sortu(dto);

            var okResult = Assert.IsType<OkObjectResult>(result);
            dynamic value = okResult.Value;
            Assert.Equal("Mahai sortuta", value.mezua);
            Assert.NotNull(savedMahaia);
            Assert.Equal(10, savedMahaia.MahaiaZbk);
        }

        [Fact]
        public void Eguneratu_OkItzultzenDu_MahaiaExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            var mahaia = new Mahaiak { Id = 5, MahaiaZbk = 5, Edukiera = 4, Egoera = "Libre" };
            mockRepo.Setup(r => r.Get(5)).Returns(mahaia);
            var dto = new MahaiakSortuDto { MahaiaZbk = 6, Edukiera = 6, Egoera = "Okupatuta" };

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Eguneratu(5, dto);

            var okResult = Assert.IsType<OkObjectResult>(result);
            dynamic value = okResult.Value;
            Assert.Equal("Eguneratuta", value.mezua);
            mockRepo.Verify(r => r.Update(mahaia), Times.Once);
        }

        [Fact]
        public void Eguneratu_NotFoundItzultzenDu_MahaiaEzExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            mockRepo.Setup(r => r.Get(999)).Returns((Mahaiak)null);
            var dto = new MahaiakSortuDto();

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Eguneratu(999, dto);

            var notFound = Assert.IsType<NotFoundObjectResult>(result);
            dynamic value = notFound.Value;
            Assert.Equal("Ez da aurkitu", value.mezua);
        }

        [Fact]
        public void Ezabatu_OkItzultzenDu_MahaiaExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            var mahaia = new Mahaiak { Id = 5, MahaiaZbk = 5, Edukiera = 4, Egoera = "Libre" };
            mockRepo.Setup(r => r.Get(5)).Returns(mahaia);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Ezabatu(5);

            var okResult = Assert.IsType<OkObjectResult>(result);
            dynamic value = okResult.Value;
            Assert.Equal("Ezabatuta", value.mezua);
            mockRepo.Verify(r => r.Delete(mahaia), Times.Once);
        }

        [Fact]
        public void Ezabatu_NotFoundItzultzenDu_MahaiaEzExistitzenDenean()
        {
            var mockRepo = new Mock<MahaiakRepository>();
            mockRepo.Setup(r => r.Get(999)).Returns((Mahaiak)null);

            var controller = new MahaiakController(mockRepo.Object);

            var result = controller.Ezabatu(999);

            var notFound = Assert.IsType<NotFoundObjectResult>(result);
            dynamic value = notFound.Value;
            Assert.Equal("Ez da aurkitu", value.mezua);
        }
    }
}