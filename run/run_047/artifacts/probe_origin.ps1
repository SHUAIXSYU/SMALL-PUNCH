$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$source = Join-Path $root 'run\run_047\artifacts\private\source_copy\508 RAW TENSILE TEST.opju'
$app = New-Object -ComObject Origin.Application
try {
    $loaded = $app.Load($source)
    Write-Output "LOADED=$loaded"
    Write-Output "WORKBOOKS=$($app.WorksheetPages.Count)"
    Write-Output "GRAPHS=$($app.GraphPages.Count)"
    for ($i=0; $i -lt $app.WorksheetPages.Count; $i++) {
        $book = $app.WorksheetPages.Item($i)
        Write-Output "BOOK[$i] name=$($book.Name) long=$($book.LongName) sheets=$($book.Layers.Count)"
        for ($j=0; $j -lt $book.Layers.Count; $j++) {
            $sheet = $book.Layers.Item($j)
            Write-Output "SHEET[$i,$j] name=$($sheet.Name) cols=$($sheet.Columns.Count) rows=$($sheet.Rows)"
            for ($k=0; $k -lt $sheet.Columns.Count; $k++) {
                $col = $sheet.Columns.Item($k)
                Write-Output "COL[$i,$j,$k] name=$($col.Name) long=$($col.LongName) units=$($col.Units) comments=$($col.Comments)"
            }
        }
    }
    for ($i=0; $i -lt $app.GraphPages.Count; $i++) {
        $graph = $app.GraphPages.Item($i)
        Write-Output "GRAPH[$i] name=$($graph.Name) long=$($graph.LongName) layers=$($graph.Layers.Count)"
    }
} finally {
    try { $app.Exit() } catch { }
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) | Out-Null
}
