using JatetxeaApi.DTOak;
using JatetxeaApi.Modeloak;
using NHibernate;
using System;
using System.Collections.Generic;
using System.Linq;
using NHSession = NHibernate.ISession;
using NHSessionFactory = NHibernate.ISessionFactory;

namespace JatetxeaApi.Repositorioak
{
    public class ZerbitzuakRepository
    {
        private readonly NHSessionFactory _sessionFactory;
        private readonly NHSession _session;

        public ZerbitzuakRepository(NHSessionFactory sessionFactory)
        {
            _sessionFactory = sessionFactory;
            _session = sessionFactory.GetCurrentSession();
        }

        public ZerbitzuakRepository()
        {
        }

        private NHSession Session
        {
            get
            {
                if (_session == null)
                    throw new InvalidOperationException("Session ez dago eskuragarri.");
                return _session;
            }
        }

        private NHSessionFactory SessionFactory
        {
            get
            {
                if (_sessionFactory == null)
                    throw new InvalidOperationException("SessionFactory ez dago eskuragarri.");
                return _sessionFactory;
            }
        }

        public virtual bool TransakzioaAktibo()
        {
            return Session.Transaction != null && Session.Transaction.IsActive;
        }

        public virtual void Add(Zerbitzuak item)
        {
            if (TransakzioaAktibo())
            {
                Session.Save(item);
                return;
            }

            using var tx = Session.BeginTransaction();
            Session.Save(item);
            tx.Commit();
        }

        public virtual Zerbitzuak? Get(int id)
        {
            return Session.Query<Zerbitzuak>().SingleOrDefault(x => x.Id == id);
        }

        public virtual IList<Zerbitzuak> GetAll()
        {
            return Session.Query<Zerbitzuak>().ToList();
        }

        public virtual Zerbitzuak? GetByErreserbaId(int erreserbaId)
        {
            return Session.Query<Zerbitzuak>()
                .FirstOrDefault(z => z.ErreserbaId.HasValue && z.ErreserbaId.Value == erreserbaId);
        }

        public virtual IList<object> GetPlaterakLaburpenaByZerbitzuaId(int zerbitzuaId)
        {
            return Session.Query<ZerbitzuXehetasunak>()
                .Where(x => x.ZerbitzuaId == zerbitzuaId)
                .ToList()
                .Select(x => (object)new
                {
                    x.PlateraId,
                    x.Kantitatea,
                    x.Zerbitzatuta
                })
                .ToList();
        }

        public virtual IList<Zerbitzuak> LortuErreserbaIdz(int erreserbaId)
        {
            return Session.Query<Zerbitzuak>()
                .Where(z => z.ErreserbaId.HasValue && z.ErreserbaId.Value == erreserbaId)
                .ToList();
        }

        public virtual int ErreserbaLoturaKendu(int erreserbaId)
        {
            if (TransakzioaAktibo())
            {
                return Session.CreateQuery("update Zerbitzuak z set z.ErreserbaId = null where z.ErreserbaId = :id")
                    .SetParameter("id", erreserbaId)
                    .ExecuteUpdate();
            }

            using var tx = Session.BeginTransaction();
            var kop = Session.CreateQuery("update Zerbitzuak z set z.ErreserbaId = null where z.ErreserbaId = :id")
                .SetParameter("id", erreserbaId)
                .ExecuteUpdate();
            tx.Commit();
            return kop;
        }

        public virtual void Update(Zerbitzuak item)
        {
            if (TransakzioaAktibo())
            {
                Session.Update(item);
                return;
            }

            using var tx = Session.BeginTransaction();
            Session.Update(item);
            tx.Commit();
        }

        public virtual void Delete(Zerbitzuak item)
        {
            if (TransakzioaAktibo())
            {
                Session.Delete(item);
                return;
            }

            using var tx = Session.BeginTransaction();
            Session.Delete(item);
            tx.Commit();
        }

        public virtual ZerbitzuaEmaitzaDto ZerbitzuaEgin(ZerbitzuaEskariaDto dto)
        {
            using var session = SessionFactory.OpenSession();
            using var tx = session.BeginTransaction();

            // 0 bada edo null bada, null bezala hartu
            int? erreserbaId = (dto.ErreserbaId == 0 || dto.ErreserbaId == null) ? null : dto.ErreserbaId;

            try
            {
                var zerbitzua = session.Query<Zerbitzuak>()
                    .FirstOrDefault(z => z.ErreserbaId == erreserbaId);

                if (zerbitzua == null)
                {
                    zerbitzua = new Zerbitzuak(dto.LangileId, dto.MahaiaId, erreserbaId, DateTime.Now, "Eskatuta", 0);
                    try
                    {
                        session.Save(zerbitzua);
                        session.Flush();
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"ERROREA ZERBITZUA SORTZEAN: {ex.Message}");
                        if (ex.InnerException != null)
                            Console.WriteLine($"INNER EXCEPTION: {ex.InnerException.Message}");
                        throw;
                    }
                }

                var xehetasunak = session.Query<ZerbitzuXehetasunak>()
                    .Where(x => x.ZerbitzuaId == zerbitzua.Id)
                    .ToList();

                foreach (var p in dto.Platerak)
                {
                    var zaharra = xehetasunak.FirstOrDefault(x => x.PlateraId == p.PlateraId);
                    var berriaKant = p.Kantitatea;

                    if (zaharra == null)
                    {
                        if (berriaKant <= 0)
                            continue;

                        var platera = session.Get<Platerak>(p.PlateraId);
                        if (platera == null)
                            throw new InvalidOperationException($"Ez da platera aurkitu: {p.PlateraId}");

                        KontsumituOsagaiak(session, p.PlateraId, berriaKant);

                        session.Save(new ZerbitzuXehetasunak
                        {
                            ZerbitzuaId = zerbitzua.Id,
                            PlateraId = p.PlateraId,
                            Kantitatea = berriaKant,
                            PrezioUnitarioa = platera.Prezioa,
                            Zerbitzatuta = false
                        });

                        continue;
                    }

                    if (zaharra.Zerbitzatuta && berriaKant < zaharra.Kantitatea)
                        berriaKant = zaharra.Kantitatea;

                    var diferentzia = berriaKant - zaharra.Kantitatea;

                    if (diferentzia > 0)
                    {
                        KontsumituOsagaiak(session, p.PlateraId, diferentzia);
                        zaharra.Kantitatea = berriaKant;
                        session.Update(zaharra);
                    }
                    else if (diferentzia < 0 && !zaharra.Zerbitzatuta)
                    {
                        ItzuliOsagaiak(session, p.PlateraId, -diferentzia);
                        zaharra.Kantitatea = berriaKant;
                        session.Update(zaharra);
                    }

                    if (zaharra.Kantitatea == 0 && !zaharra.Zerbitzatuta)
                    {
                        session.Delete(zaharra);
                    }
                }

                var xeheList = session.Query<ZerbitzuXehetasunak>()
                    .Where(x => x.ZerbitzuaId == zerbitzua.Id)
                    .ToList();

                zerbitzua.Guztira = xeheList.Any()
                    ? xeheList.Sum(x => x.PrezioUnitarioa * x.Kantitatea)
                    : 0;

                session.Update(zerbitzua);
                tx.Commit();

                return new ZerbitzuaEmaitzaDto
                {
                    Ondo = true,
                    ZerbitzuaId = zerbitzua.Id,
                    Erroreak = new List<ZerbitzuErroreaDto>()
                };
            }
            catch
            {
                if (tx.IsActive)
                    tx.Rollback();

                throw;
            }
        }

        private void KontsumituOsagaiak(NHSession session, int plateraId, int kantitatea)
        {
            var osagaiak = session.Query<PlaterenOsagaiak>()
                .Where(o => o.PlateraId == plateraId)
                .ToList();

            foreach (var o in osagaiak)
            {
                var inv = session.Get<Inbentarioa>(o.InbentarioaId);
                if (inv == null)
                    throw new InvalidOperationException($"Ez da inbentarioko osagaia aurkitu: {o.InbentarioaId}");

                session.Lock(inv, LockMode.Upgrade);
                inv.Kantitatea -= (int)(o.Kantitatea * kantitatea);
                inv.AzkenEguneratzea = DateTime.Now;
                session.Update(inv);
            }
        }

        private void ItzuliOsagaiak(NHSession session, int plateraId, int kantitatea)
        {
            var osagaiak = session.Query<PlaterenOsagaiak>()
                .Where(o => o.PlateraId == plateraId)
                .ToList();

            foreach (var o in osagaiak)
            {
                var inv = session.Get<Inbentarioa>(o.InbentarioaId);
                if (inv == null)
                    throw new InvalidOperationException($"Ez da inbentarioko osagaia aurkitu: {o.InbentarioaId}");

                session.Lock(inv, LockMode.Upgrade);
                inv.Kantitatea += (int)(o.Kantitatea * kantitatea);
                inv.AzkenEguneratzea = DateTime.Now;
                session.Update(inv);
            }
        }
    }
}