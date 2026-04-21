using JatetxeaApi.Modeloak;
using NHibernate;
using System.Collections.Generic;
using System.Linq;
using NHSession = NHibernate.ISession;
using NHSessionFactory = NHibernate.ISessionFactory;

namespace JatetxeaApi.Repositorioak
{
    public class PlaterakRepository
    {
        private readonly NHSession _session;

        public PlaterakRepository(NHSessionFactory sessionFactory)
        {
            _session = sessionFactory.GetCurrentSession();
        }

        public PlaterakRepository()
        {
        }

        public virtual void Add(Platerak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Save(item);
            tx.Commit();
        }

        public virtual Platerak? Get(int id)
        {
            return _session.Query<Platerak>().SingleOrDefault(x => x.Id == id);
        }

        public virtual Platerak? Get(String izena)
        {
            return _session.Query<Platerak>().SingleOrDefault(x => x.Izena == izena);
        }

        public virtual IList<Platerak> GetAll()
        {
            return _session.Query<Platerak>().ToList();
        }

        public virtual void Update(Platerak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Update(item);
            tx.Commit();
        }

        public virtual void Delete(Platerak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Delete(item);
            tx.Commit();
        }
    }
}
