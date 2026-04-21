using FluentNHibernate.Cfg;
using FluentNHibernate.Cfg.Db;
using JatetxeaApi.Mapeoak;
using NHibernate;
using NHibernate.Tool.hbm2ddl;

namespace JatetxeaApi
{
    public class NHibernateHelper
    {
        private static ISessionFactory _sessionFactory;
        private static NHibernate.Cfg.Configuration _configuration;

        public static ISessionFactory SessionFactory =>
            _sessionFactory ??= CreateSessionFactory();

        public static NHibernate.Cfg.Configuration Configuration =>
            _configuration ??= CreateConfiguration();

        private static ISessionFactory CreateSessionFactory()
        {
            return Configuration.BuildSessionFactory();
        }

        private static NHibernate.Cfg.Configuration CreateConfiguration()
        {
            return Fluently.Configure()
                .Database(MySQLConfiguration.Standard
                    .ConnectionString("Server=localhost;Port=3306;Database=jatetxea;Uid=root;Pwd=1MG2024;"))
                .Mappings(m =>
                {
                    m.FluentMappings.AddFromAssemblyOf<InbentarioaMap>();
                    m.FluentMappings.AddFromAssemblyOf<PlaterenOsagaiakMap>();
                    m.FluentMappings.AddFromAssemblyOf<PlaterakMap>();
                    m.FluentMappings.AddFromAssemblyOf<ZerbitzuXehetasunakMap>();
                    m.FluentMappings.AddFromAssemblyOf<KategoriaMap>();
                    m.FluentMappings.AddFromAssemblyOf<ZerbituzakMap>();
                    m.FluentMappings.AddFromAssemblyOf<LangileakMap>();
                    m.FluentMappings.AddFromAssemblyOf<RolakMap>();
                    m.FluentMappings.AddFromAssemblyOf<MahaiakMap>();
                    m.FluentMappings.AddFromAssemblyOf<ErreserbakMap>();
                    m.FluentMappings.AddFromAssemblyOf<JatetxekoInfoMap>();
                })
                .ExposeConfiguration(cfg =>
                {
                    cfg.SetProperty("current_session_context_class", "async_local");
                })
                .BuildConfiguration();
        }

        public static void dbEguneratu(NHibernate.Cfg.Configuration config)
        {
            var schemaUpdate = new SchemaUpdate(config);
            schemaUpdate.Execute(false, true);
        }

        public static void dbBirSortu(NHibernate.Cfg.Configuration config)
        {
            var schemaExport = new SchemaExport(config);
            schemaExport.Drop(true, true);
            schemaExport.Create(true, true);
        }
    }
}
