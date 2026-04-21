using JatetxeaApi.Modeloak;
using JatetxeaApi.DTOak;
using JatetxeaApi.Repositorioak;
using Microsoft.AspNetCore.Mvc;
using System.Linq;

namespace JatetxeaApi.Controllerrak
{
    [ApiController]
    [Route("api/[controller]")]
    public class MahaiakController : ControllerBase
    {
        private readonly MahaiakRepository _repo;

        public MahaiakController(MahaiakRepository repo)
        {
            _repo = repo;
        }

        /// <summary>
        /// Mahai guztiak lortzen ditu
        /// </summary>
        [HttpGet]
        public IActionResult GetAll()
        {
            var lista = _repo.GetAll().Select(m => new MahaiakDto
            {
                Id = m.Id,
                MahaiaZbk = m.MahaiaZbk,
                Edukiera = m.Edukiera,
                Egoera = m.Egoera
            });

            return Ok(lista);
        }

        /// <summary>
        /// Id zehatz bateko mahai bat lortzen du
        /// </summary>
        [HttpGet("{id}")]
        public IActionResult Get(int id)
        {
            var m = _repo.Get(id);
            if (m == null) return NotFound(new { mezua = "Ez da aurkitu" });

            return Ok(new MahaiakDto
            {
                Id = m.Id,
                MahaiaZbk = m.MahaiaZbk,
                Edukiera = m.Edukiera,
                Egoera = m.Egoera
            });
        }

        /// <summary>
        /// Mahai berria sortzen du
        /// </summary>
        [HttpPost]
        public IActionResult Sortu([FromBody] MahaiakSortuDto dto)
        {
            var m = new Mahaiak(dto.MahaiaZbk, dto.Edukiera, dto.Egoera);
            _repo.Add(m);
            return Ok(new { mezua = "Mahai sortuta", id = m.Id });
        }

        /// <summary>
        /// Id zehatz bateko mahai bat eguneratzen du
        /// </summary>
        [HttpPut("{id}")]
        public IActionResult Eguneratu(int id, [FromBody] MahaiakSortuDto dto)
        {
            var m = _repo.Get(id);
            if (m == null) return NotFound(new { mezua = "Ez da aurkitu" });

            m.MahaiaZbk = dto.MahaiaZbk;
            m.Edukiera = dto.Edukiera;
            m.Egoera = dto.Egoera;

            _repo.Update(m);
            return Ok(new { mezua = "Eguneratuta" });
        }

        /// <summary>
        /// Id zehatz bateko mahai bat ezabatzen du
        /// </summary>
        [HttpDelete("{id}")]
        public IActionResult Ezabatu(int id)
        {
            var m = _repo.Get(id);
            if (m == null) return NotFound(new { mezua = "Ez da aurkitu" });

            _repo.Delete(m);
            return Ok(new { mezua = "Ezabatuta" });
        }
    }
}