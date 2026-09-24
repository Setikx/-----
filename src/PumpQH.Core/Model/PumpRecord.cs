using System.Text.Json.Serialization;

namespace PumpQH.Core.Model;

/// <summary>Тип рабочего колеса / гидравлики.</summary>
public enum ImpellerType
{
    Unknown,
    /// <summary>Свободновихревое (Vortex).</summary>
    Vortex,
    /// <summary>Одноканальное.</summary>
    SingleChannel,
    /// <summary>Двух- и многоканальное.</summary>
    MultiChannel,
    /// <summary>Открытое / полуоткрытое.</summary>
    Open,
    /// <summary>С режущим механизмом (режущие кромки, нож на входе).</summary>
    Cutter,
    /// <summary>Измельчитель (grinder) — напорная канализация малых диаметров.</summary>
    Grinder,
}

/// <summary>Происхождение характеристики: насколько ей можно доверять.</summary>
public enum CurveQuality
{
    /// <summary>Таблица точек Q–H из каталога изготовителя.</summary>
    CatalogTable,
    /// <summary>Только номинальная точка (или Qmax/Hmax/Qopt/Hopt) из каталога; форма кривой аппроксимирована.</summary>
    CatalogNominal,
    /// <summary>Введено пользователем.</summary>
    User,
}

public sealed class CurvePoint
{
    public double Q { get; set; }
    public double V { get; set; }
    public CurvePoint() { }
    public CurvePoint(double q, double v) { Q = q; V = v; }
    public override string ToString() => $"({Q:0.##}; {V:0.##})";
}

/// <summary>Паспортные кривые насоса при номинальной частоте вращения и полном колесе. Q — м³/ч.</summary>
public sealed class PumpCurve
{
    /// <summary>Напор, м.</summary>
    public List<CurvePoint> QH { get; set; } = new();
    /// <summary>Мощность на валу P2, кВт (если есть в каталоге).</summary>
    public List<CurvePoint> QP { get; set; } = new();
    /// <summary>КПД насоса, % (если есть).</summary>
    public List<CurvePoint> QEta { get; set; } = new();
    /// <summary>NPSH required, м (если есть).</summary>
    public List<CurvePoint> QNpsh { get; set; } = new();
}

public sealed class SourceInfo
{
    public string Document { get; set; } = "";
    public string Url { get; set; } = "";
    public string Date { get; set; } = "";
    public CurveQuality Quality { get; set; } = CurveQuality.CatalogNominal;
}

/// <summary>Запись базы насосов.</summary>
public sealed class PumpRecord
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];
    public string Manufacturer { get; set; } = "";
    public string Series { get; set; } = "";
    public string Model { get; set; } = "";
    public string Country { get; set; } = "";
    /// <summary>Назначение: «канализационный», «дренажный», «водопроводный» и т.п.</summary>
    public string Application { get; set; } = "канализационный погружной";
    public ImpellerType Impeller { get; set; } = ImpellerType.Unknown;
    public bool HasCutter { get; set; }
    /// <summary>Напорный патрубок, мм.</summary>
    public int DnOut { get; set; }
    /// <summary>Свободный проход, мм (0 — неизвестно).</summary>
    public double FreePassageMm { get; set; }
    /// <summary>Номинальная мощность двигателя P2, кВт.</summary>
    public double P2Kw { get; set; }
    /// <summary>Потребляемая мощность P1, кВт (0 — неизвестно).</summary>
    public double P1Kw { get; set; }
    public int Rpm { get; set; } = 2900;
    public int Poles { get; set; } = 2;
    public string Voltage { get; set; } = "3~400 В";
    public double WeightKg { get; set; }
    /// <summary>Момент инерции вращающихся частей агрегата, кг·м² (0 — оценивается).</summary>
    public double InertiaKgM2 { get; set; }
    /// <summary>Диаметр рабочего колеса, мм (0 — неизвестен, обточка считается в долях).</summary>
    public double ImpellerDmm { get; set; }
    /// <summary>Минимально допустимая обточка (доля номинального диаметра).</summary>
    public double TrimMin { get; set; } = 0.85;
    /// <summary>Минимально допустимая частота вращения при ЧРП (доля номинальной).</summary>
    public double SpeedMin { get; set; } = 0.6;
    /// <summary>Номинальная (каталожная) точка.</summary>
    public double NominalQ { get; set; }
    public double NominalH { get; set; }
    public double NominalEta { get; set; }
    /// <summary>Рекомендуемый рабочий диапазон подачи, м³/ч (0 — оценивается по кривой).</summary>
    public double RangeQmin { get; set; }
    public double RangeQmax { get; set; }
    public PumpCurve Curve { get; set; } = new();
    public SourceInfo Source { get; set; } = new();
    public string Notes { get; set; } = "";

    /// <summary>Изготовитель + модель; если обозначение модели уже начинается с имени изготовителя, оно не дублируется.</summary>
    [JsonIgnore]
    public string FullName
    {
        get
        {
            var first = Manufacturer.Split(' ', '(')[0].Trim();
            if (first.Length > 0 && Model.StartsWith(first, StringComparison.OrdinalIgnoreCase)) return Model.Trim();
            return $"{Manufacturer} {Model}".Trim();
        }
    }

    [JsonIgnore] public string ImpellerText => Impeller switch
    {
        ImpellerType.Vortex => "свободновихревое",
        ImpellerType.SingleChannel => "одноканальное",
        ImpellerType.MultiChannel => "многоканальное",
        ImpellerType.Open => "открытое",
        ImpellerType.Cutter => "с режущим механизмом",
        ImpellerType.Grinder => "измельчитель",
        _ => "—",
    };

    [JsonIgnore] public string QualityText => Source.Quality switch
    {
        CurveQuality.CatalogTable => "таблица каталога",
        CurveQuality.CatalogNominal => "номинал каталога, форма аппроксимирована",
        CurveQuality.User => "введено пользователем",
        _ => "",
    };

    /// <summary>Тип рабочей области: паспортная (задана изготовителем) или расчётная по ANSI/HI 9.6.3.</summary>
    [JsonIgnore] public string RangeSourceShort => RangeQmin > 0 || RangeQmax > 0 ? "паспорт" : "расчёт";

    [JsonIgnore] public double Hmax => Curve.QH.Count == 0 ? 0 : Curve.QH.Max(p => p.V);
    [JsonIgnore] public double Qmax => Curve.QH.Count == 0 ? 0 : Curve.QH.Max(p => p.Q);

    public override string ToString() => FullName;
}
