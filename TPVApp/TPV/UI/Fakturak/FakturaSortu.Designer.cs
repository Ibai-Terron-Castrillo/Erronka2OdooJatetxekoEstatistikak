using System.Drawing;
using System.Windows.Forms;

namespace TPV.BISTAK
{
    partial class FakturaSortu
    {
        private System.ComponentModel.IContainer components = null;
        private TableLayoutPanel layoutNagusia;
        private Panel headerPanel;
        private Label lblIzenburua;
        private FlowLayoutPanel zerbitzuakPanel;
        private Label lblMezua;

        // Deskuntu kontrolak
        private Panel deskuntuPanel;
        private Label lblDeskuntuKodea;
        private TextBox txtDeskuntuKodea;
        private Button btnDeskuntuBalidatu;
        private Label lblDeskuntuEgoera;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null)) components.Dispose();
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            layoutNagusia = new TableLayoutPanel();
            headerPanel = new Panel();
            lblIzenburua = new Label();
            zerbitzuakPanel = new FlowLayoutPanel();
            lblMezua = new Label();

            // Deskuntu kontrolak hasieratu
            deskuntuPanel = new Panel();
            lblDeskuntuKodea = new Label();
            txtDeskuntuKodea = new TextBox();
            btnDeskuntuBalidatu = new Button();
            lblDeskuntuEgoera = new Label();

            layoutNagusia.SuspendLayout();
            headerPanel.SuspendLayout();
            zerbitzuakPanel.SuspendLayout();
            deskuntuPanel.SuspendLayout();
            SuspendLayout();

            layoutNagusia.ColumnCount = 1;
            layoutNagusia.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            layoutNagusia.Controls.Add(headerPanel, 0, 0);
            layoutNagusia.Controls.Add(deskuntuPanel, 0, 1);
            layoutNagusia.Controls.Add(zerbitzuakPanel, 0, 2);
            layoutNagusia.Dock = DockStyle.Fill;
            layoutNagusia.Location = new Point(0, 0);
            layoutNagusia.Name = "layoutNagusia";
            layoutNagusia.RowCount = 3;
            layoutNagusia.RowStyles.Add(new RowStyle(SizeType.Absolute, 60F));
            layoutNagusia.RowStyles.Add(new RowStyle(SizeType.Absolute, 60F));
            layoutNagusia.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            layoutNagusia.Size = new Size(900, 600);
            layoutNagusia.TabIndex = 0;

            headerPanel.BackColor = Color.Black;
            headerPanel.Controls.Add(lblIzenburua);
            headerPanel.Dock = DockStyle.Fill;
            headerPanel.Location = new Point(3, 3);
            headerPanel.Name = "headerPanel";
            headerPanel.Size = new Size(894, 54);
            headerPanel.TabIndex = 0;

            lblIzenburua.Dock = DockStyle.Fill;
            lblIzenburua.Font = new System.Drawing.Font("Segoe UI", 20F, FontStyle.Bold);
            lblIzenburua.ForeColor = Color.Goldenrod;
            lblIzenburua.Location = new Point(0, 0);
            lblIzenburua.Name = "lblIzenburua";
            lblIzenburua.Size = new Size(894, 54);
            lblIzenburua.TabIndex = 0;
            lblIzenburua.Text = "Fakturak";
            lblIzenburua.TextAlign = ContentAlignment.MiddleCenter;

            // Deskuntu panela
            deskuntuPanel.BackColor = Color.LightGray;
            deskuntuPanel.Controls.Add(lblDeskuntuEgoera);
            deskuntuPanel.Controls.Add(btnDeskuntuBalidatu);
            deskuntuPanel.Controls.Add(txtDeskuntuKodea);
            deskuntuPanel.Controls.Add(lblDeskuntuKodea);
            deskuntuPanel.Dock = DockStyle.Fill;
            deskuntuPanel.Location = new Point(3, 63);
            deskuntuPanel.Name = "deskuntuPanel";
            deskuntuPanel.Size = new Size(894, 54);
            deskuntuPanel.TabIndex = 1;

            lblDeskuntuKodea.AutoSize = true;
            lblDeskuntuKodea.Font = new System.Drawing.Font("Segoe UI", 10F, FontStyle.Bold);
            lblDeskuntuKodea.Location = new Point(20, 18);
            lblDeskuntuKodea.Name = "lblDeskuntuKodea";
            lblDeskuntuKodea.Size = new Size(120, 19);
            lblDeskuntuKodea.TabIndex = 0;
            lblDeskuntuKodea.Text = "Deskuntu kodea:";

            txtDeskuntuKodea.Font = new System.Drawing.Font("Segoe UI", 10F);
            txtDeskuntuKodea.Location = new Point(150, 15);
            txtDeskuntuKodea.Name = "txtDeskuntuKodea";
            txtDeskuntuKodea.Size = new Size(150, 25);
            txtDeskuntuKodea.TabIndex = 1;
            txtDeskuntuKodea.CharacterCasing = CharacterCasing.Upper;

            btnDeskuntuBalidatu.Font = new System.Drawing.Font("Segoe UI", 10F);
            btnDeskuntuBalidatu.Location = new Point(310, 13);
            btnDeskuntuBalidatu.Name = "btnDeskuntuBalidatu";
            btnDeskuntuBalidatu.Size = new Size(100, 28);
            btnDeskuntuBalidatu.TabIndex = 2;
            btnDeskuntuBalidatu.Text = "Balidatu";
            btnDeskuntuBalidatu.UseVisualStyleBackColor = true;

            lblDeskuntuEgoera.AutoSize = true;
            lblDeskuntuEgoera.Font = new System.Drawing.Font("Segoe UI", 10F, FontStyle.Bold);
            lblDeskuntuEgoera.Location = new Point(430, 18);
            lblDeskuntuEgoera.Name = "lblDeskuntuEgoera";
            lblDeskuntuEgoera.Size = new Size(0, 19);
            lblDeskuntuEgoera.TabIndex = 3;

            zerbitzuakPanel.AutoScroll = true;
            zerbitzuakPanel.Controls.Add(lblMezua);
            zerbitzuakPanel.Dock = DockStyle.Fill;
            zerbitzuakPanel.Location = new Point(3, 123);
            zerbitzuakPanel.Name = "zerbitzuakPanel";
            zerbitzuakPanel.Size = new Size(894, 474);
            zerbitzuakPanel.TabIndex = 2;

            lblMezua.Dock = DockStyle.Fill;
            lblMezua.Font = new System.Drawing.Font("Segoe UI", 14F, FontStyle.Bold);
            lblMezua.Location = new Point(3, 0);
            lblMezua.Name = "lblMezua";
            lblMezua.Size = new Size(100, 0);
            lblMezua.TabIndex = 0;
            lblMezua.Text = "Zerbitzuak kargatzen...";
            lblMezua.TextAlign = ContentAlignment.MiddleCenter;

            BackColor = Color.White;
            ClientSize = new Size(900, 600);
            Controls.Add(layoutNagusia);
            MinimumSize = new Size(900, 600);
            Name = "FakturaSortu";
            Text = "Fakturak";
            WindowState = FormWindowState.Maximized;

            layoutNagusia.ResumeLayout(false);
            headerPanel.ResumeLayout(false);
            deskuntuPanel.ResumeLayout(false);
            deskuntuPanel.PerformLayout();
            zerbitzuakPanel.ResumeLayout(false);
            ResumeLayout(false);
        }
    }
}