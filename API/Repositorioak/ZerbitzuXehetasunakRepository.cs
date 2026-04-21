using JatetxeaApi.Modeloak;
using NHibernate;
using System.Collections.Generic;
using System.Linq;
using NHSession = NHibernate.ISession;
using NHSessionFactory = NHibernate.ISessionFactory;

namespace JatetxeaApi.Repositorioak
{
    public class ZerbitzuXehetasunakRepository
    {
        private readonly NHSession _session;

        public ZerbitzuXehetasunakRepository(NHSessionFactory sessionFactory)
        {
            _session = sessionFactory.GetCurrentSession();
        }

        public ZerbitzuXehetasunakRepository()
        {
        }


        public virtual void Add(ZerbitzuXehetasunak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Save(item);
            tx.Commit();
        }

        public virtual ZerbitzuXehetasunak? Get(int id)
        {
            return _session.Query<ZerbitzuXehetasunak>().SingleOrDefault(x => x.Id == id);
        }

        public virtual IList<ZerbitzuXehetasunak> GetAll()
        {
            return _session.Query<ZerbitzuXehetasunak>().ToList();
        }

        public virtual void Update(ZerbitzuXehetasunak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Update(item);
            tx.Commit();
        }

        public virtual void Delete(ZerbitzuXehetasunak item)
        {
            using var tx = _session.BeginTransaction();
            _session.Delete(item);
            tx.Commit();
        }
    }
}
