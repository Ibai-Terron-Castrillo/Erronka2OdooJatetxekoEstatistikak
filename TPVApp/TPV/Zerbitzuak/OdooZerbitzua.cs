using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace TPV.Zerbitzuak
{
    public class OdooZerbitzua
    {
        private readonly HttpClient _bezeroa;
        private readonly string _odooApiUrl;

        public const string ODOO_API_OINARRIA = "http://192.168.10.5:8085";

        public OdooZerbitzua(string? odooUrl = null)
        {
            _odooApiUrl = odooUrl ?? ODOO_API_OINARRIA;
            _bezeroa = new HttpClient
            {
                BaseAddress = new Uri(_odooApiUrl),
                Timeout = TimeSpan.FromSeconds(30)
            };
        }

        /// <summary>
        /// Deskuntu kodea balidatu Odoo-n
        /// </summary>
        public async Task<DeskuntuEmaitza> DeskuntuBalidatuAsync(string kodea)
        {
            try
            {
                // Odoo-k "code" edo "discount_code" espero dezake. Behar izanez gero aldatu.
                var payload = new { code = kodea };
                var json = JsonSerializer.Serialize(payload);
                var edukia = new StringContent(json, Encoding.UTF8, "application/json");

                var erantzuna = await _bezeroa.PostAsync("/api/discount/validate", edukia);

                if (erantzuna.IsSuccessStatusCode)
                {
                    var testua = await erantzuna.Content.ReadAsStringAsync();
                    var emaitza = JsonSerializer.Deserialize<DeskuntuEmaitza>(testua, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    return emaitza ?? new DeskuntuEmaitza { Valid = false, Message = "Erantzun hutsa" };
                }
                else
                {
                    var erroreTestua = await erantzuna.Content.ReadAsStringAsync();
                    return new DeskuntuEmaitza
                    {
                        Valid = false,
                        Message = $"API errorea ({erantzuna.StatusCode}): {erroreTestua}"
                    };
                }
            }
            catch (Exception ex)
            {
                return new DeskuntuEmaitza
                {
                    Valid = false,
                    Message = $"Konexio errorea: {ex.Message}"
                };
            }
        }

        /// <summary>
        /// Deskuntu kodea aplikatu eskaera bati
        /// </summary>
        public async Task<DeskuntuEmaitza> DeskuntuAplikatuAsync(string kodea, int? eskaeraId = null)
        {
            try
            {
                var payload = new { code = kodea, order_id = eskaeraId };
                var json = JsonSerializer.Serialize(payload);
                var edukia = new StringContent(json, Encoding.UTF8, "application/json");

                var erantzuna = await _bezeroa.PostAsync("/api/discount/apply", edukia);

                if (erantzuna.IsSuccessStatusCode)
                {
                    var testua = await erantzuna.Content.ReadAsStringAsync();
                    var emaitza = JsonSerializer.Deserialize<DeskuntuEmaitza>(testua, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    return emaitza ?? new DeskuntuEmaitza { Valid = false, Message = "Erantzun hutsa" };
                }
                else
                {
                    var erroreTestua = await erantzuna.Content.ReadAsStringAsync();
                    return new DeskuntuEmaitza
                    {
                        Valid = false,
                        Message = $"API errorea ({erantzuna.StatusCode}): {erroreTestua}"
                    };
                }
            }
            catch (Exception ex)
            {
                return new DeskuntuEmaitza
                {
                    Valid = false,
                    Message = $"Konexio errorea: {ex.Message}"
                };
            }
        }

        public async Task<SinkronizazioEmaitza> SinkronizazioEgoeraAsync()
        {
            try
            {
                var erantzuna = await _bezeroa.GetAsync("/api/sync/status");

                if (erantzuna.IsSuccessStatusCode)
                {
                    var testua = await erantzuna.Content.ReadAsStringAsync();
                    var emaitza = JsonSerializer.Deserialize<SinkronizazioEmaitza>(testua, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    return emaitza ?? new SinkronizazioEmaitza { Status = "error", ErrorMessage = "Erantzun hutsa" };
                }
                else
                {
                    var erroreTestua = await erantzuna.Content.ReadAsStringAsync();
                    return new SinkronizazioEmaitza
                    {
                        Status = "error",
                        ErrorMessage = $"API errorea ({erantzuna.StatusCode}): {erroreTestua}"
                    };
                }
            }
            catch (Exception ex)
            {
                return new SinkronizazioEmaitza
                {
                    Status = "error",
                    ErrorMessage = $"Konexio errorea: {ex.Message}"
                };
            }
        }
    }

    public class DeskuntuEmaitza
    {
        public bool Valid { get; set; }
        public string Message { get; set; }
        public double Percentage { get; set; }
        public int? CodeId { get; set; }
    }

    public class SinkronizazioEmaitza
    {
        public string Status { get; set; }
        public string SyncType { get; set; }
        public int RecordsSynced { get; set; }
        public string ErrorMessage { get; set; }
        public DateTime? LastSync { get; set; }
    }
}