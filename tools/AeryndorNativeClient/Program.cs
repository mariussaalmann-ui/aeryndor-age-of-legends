using System;
using System.Windows.Forms;

namespace AeryndorClient;

static class Program
{
    [STAThread]
    static void Main()
    {
        try
        {
            ApplicationConfiguration.Initialize();
            Application.Run(new Form1());
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "Aeryndor Startup Error");
        }
    }
}
