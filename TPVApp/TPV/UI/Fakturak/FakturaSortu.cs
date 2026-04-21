using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using TPV.MODELOAK;
using OdooZerbitzua = TPV.Zerbitzuak.OdooZerbitzua;

namespace TPV.BISTAK
{
    public partial class FakturaSortu : Form
    {
        private readonly HttpClient bezeroa;
        private readonly int langileId;
        private readonly OdooZerbitzua odooZerbitzua;
        private const string ApiOinarria = "http://192.168.10.5:5093";

        private List<TPV.MODELOAK.Zerbitzuak> zerbitzuak = new();
        private double deskuntuEhunekoa = 0;
        private int? deskuntuKodeId = null;

        public FakturaSortu(int langileIdPasatua)
        {
            InitializeComponent();
            bezeroa = new HttpClient();
            langileId = langileIdPasatua;
            odooZerbitzua = new OdooZerbitzua();

            btnDeskuntuBalidatu.Click += BtnDeskuntuBalidatu_Click;
            _ = KargatuZerbitzatuak();
        }

        private async void BtnDeskuntuBalidatu_Click(object? sender, EventArgs e)
        {
            string kodea = txtDeskuntuKodea.Text.Trim().ToUpper();

            // Kodea hutsik badago, deskuntua desaktibatu
            if (string.IsNullOrEmpty(kodea))
            {
                deskuntuEhunekoa = 0;
                deskuntuKodeId = null;
                lblDeskuntuEgoera.Text = "Deskunturik gabe";
                lblDeskuntuEgoera.ForeColor = Color.Black;
                txtDeskuntuKodea.ReadOnly = false;
                btnDeskuntuBalidatu.Text = "Balidatu";
                return;
            }

            btnDeskuntuBalidatu.Enabled = false;
            btnDeskuntuBalidatu.Text = "Balidatzen...";
            lblDeskuntuEgoera.Text = "";
            lblDeskuntuEgoera.ForeColor = Color.Black;

            try
            {
                var emaitza = await odooZerbitzua.DeskuntuBalidatuAsync(kodea);

                if (emaitza.Valid)
                {
                    deskuntuEhunekoa = emaitza.Percentage;
                    deskuntuKodeId = emaitza.CodeId;
                    lblDeskuntuEgoera.Text = $"Deskuntu baliozkoa: %{emaitza.Percentage}";
                    lblDeskuntuEgoera.ForeColor = Color.Green;
                    txtDeskuntuKodea.ReadOnly = true;
                    btnDeskuntuBalidatu.Text = "Baliozkoa";
                }
                else
                {
                    deskuntuEhunekoa = 0;
                    deskuntuKodeId = null;
                    lblDeskuntuEgoera.Text = emaitza.Message ?? "Kodea ez da baliozkoa";
                    lblDeskuntuEgoera.ForeColor = Color.Red;
                    btnDeskuntuBalidatu.Text = "Balidatu";
                    txtDeskuntuKodea.ReadOnly = false;
                    // Ez da ordainketa blokeatzen
                }
            }
            catch (Exception ex)
            {
                deskuntuEhunekoa = 0;
                deskuntuKodeId = null;
                lblDeskuntuEgoera.Text = $"Errorea: {ex.Message}";
                lblDeskuntuEgoera.ForeColor = Color.Red;
                btnDeskuntuBalidatu.Text = "Balidatu";
                txtDeskuntuKodea.ReadOnly = false;
            }
            finally
            {
                btnDeskuntuBalidatu.Enabled = true;
            }
        }

        private async Task KargatuZerbitzatuak()
        {
            try
            {
                lblMezua.Text = "Zerbitzuak kargatzen...";
                lblMezua.Visible = true;

                var denak = await bezeroa.GetFromJsonAsync<List<TPV.MODELOAK.Zerbitzuak>>(ApiOinarria + "/api/Zerbitzuak");
                if (denak != null)
                {
                    zerbitzuak = denak.Where(z => z.Egoera != "Ordainduta").ToList();
                }

                AzalduZerbitzuak();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Errorea zerbitzuak kargatzean: " + ex.Message);
            }
        }

        private void AzalduZerbitzuak()
        {
            zerbitzuakPanel.Controls.Clear();

            if (!zerbitzuak.Any())
            {
                lblMezua.Text = "Ez dago ordaindu gabeko zerbitzurik.";
                lblMezua.Visible = true;
                zerbitzuakPanel.Controls.Add(lblMezua);
                return;
            }

            lblMezua.Visible = false;

            foreach (var z in zerbitzuak)
            {
                zerbitzuakPanel.Controls.Add(SortuZerbitzuTxartela(z));
            }
        }

        private Control SortuZerbitzuTxartela(TPV.MODELOAK.Zerbitzuak z)
        {
            var card = new Panel
            {
                Width = 400,
                Height = 150,
                BackColor = Color.White,
                BorderStyle = BorderStyle.FixedSingle,
                Margin = new Padding(10)
            };

            var lblMahaia = new Label
            {
                Text = $"Mahaia: {z.MahaiaId}",
                Font = new Font("Segoe UI", 12F, FontStyle.Bold),
                Location = new Point(10, 10),
                AutoSize = true
            };

            var lblPrezioa = new Label
            {
                Text = $"Guztira: {z.Guztira:C2}",
                Font = new Font("Segoe UI", 10F),
                Location = new Point(10, 40),
                AutoSize = true
            };

            var btnOrdaindu = new Button
            {
                Text = "Ordaindu eta Ticket",
                Width = 150,
                Height = 40,
                Location = new Point(10, 80),
                BackColor = Color.Green,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };

            btnOrdaindu.Click += async (_, __) => await TicketDeskargatu(z);

            card.Controls.Add(lblMahaia);
            card.Controls.Add(lblPrezioa);
            card.Controls.Add(btnOrdaindu);

            return card;
        }

        private async Task TicketDeskargatu(TPV.MODELOAK.Zerbitzuak z)
        {
            try
            {
                // Deskuntua aplikatu behar bada Odoo-n
                if (deskuntuKodeId.HasValue && !string.IsNullOrEmpty(txtDeskuntuKodea.Text))
                {
                    var aplikatuRes = await odooZerbitzua.DeskuntuAplikatuAsync(txtDeskuntuKodea.Text, z.Id);
                    if (!aplikatuRes.Valid)
                    {
                        MessageBox.Show($"Abisua: Deskuntua ezin izan da Odoo-n aplikatu: {aplikatuRes.Message}");
                    }
                }

                // PDFa sortu (Simulazioa edo oinarrizkoa)
                SortuPdfTicket(z);

                // APIan ordainduta bezala markatu
                var ondo = await OrdainduMarkatu(z);
                if (ondo)
                {
                    MessageBox.Show("Zerbitzua ordainduta markatu da.");
                    await KargatuZerbitzatuak();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Errorea ordainketa prozesatzean: " + ex.Message);
            }
        }

        private async Task<bool> OrdainduMarkatu(TPV.MODELOAK.Zerbitzuak z)
        {
            z.Egoera = "Ordainduta";
            var res = await bezeroa.PutAsJsonAsync($"{ApiOinarria}/api/Zerbitzuak/{z.Id}", z);
            return res.IsSuccessStatusCode;
        }

        private void SortuPdfTicket(TPV.MODELOAK.Zerbitzuak z)
        {
            // PDFSharpCore erabiliz PDF bat sortzeko adibide oso oinarrizkoa
            try
            {
                using (var document = new PdfSharpCore.Pdf.PdfDocument())
                {
                    var page = document.AddPage();
                    var gfx = PdfSharpCore.Drawing.XGraphics.FromPdfPage(page);
                    var fontBold = new PdfSharpCore.Drawing.XFont("Verdana", 20, PdfSharpCore.Drawing.XFontStyle.Bold);
                    var fontNormal = new PdfSharpCore.Drawing.XFont("Verdana", 12, PdfSharpCore.Drawing.XFontStyle.Regular);

                    gfx.DrawString("JATETXEA TICKET", fontBold, PdfSharpCore.Drawing.XBrushes.Black, new PdfSharpCore.Drawing.XRect(0, 0, page.Width, 50), PdfSharpCore.Drawing.XStringFormats.Center);
                    gfx.DrawString($"Mahaia: {z.MahaiaId}", fontNormal, PdfSharpCore.Drawing.XBrushes.Black, 50, 100);
                    gfx.DrawString($"Data: {DateTime.Now:yyyy-MM-dd HH:mm}", fontNormal, PdfSharpCore.Drawing.XBrushes.Black, 50, 120);
                    
                    decimal guztira = z.Guztira ?? 0;
                    if (deskuntuEhunekoa > 0)
                    {
                        decimal deskuntua = guztira * (decimal)(deskuntuEhunekoa / 100.0);
                        gfx.DrawString($"Azpitotala: {guztira:C2}", fontNormal, PdfSharpCore.Drawing.XBrushes.Black, 50, 160);
                        gfx.DrawString($"Deskuntua (%{deskuntuEhunekoa}): -{deskuntua:C2}", fontNormal, PdfSharpCore.Drawing.XBrushes.Black, 50, 180);
                        guztira -= deskuntua;
                    }

                    gfx.DrawString($"GUZTIRA: {guztira:C2}", fontBold, PdfSharpCore.Drawing.XBrushes.Black, 50, 220);

                    string fitxategia = $"Ticket_{z.Id}_{DateTime.Now:HHmmss}.pdf";
                    document.Save(fitxategia);
                    MessageBox.Show($"Ticket-a sortua: {fitxategia}");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Errorea PDFa sortzean: " + ex.Message);
            }
        }
    }
}