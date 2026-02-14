import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function HelpPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Help</h1>
        <p className="text-muted-foreground mt-1">Guide and documentation</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>DiaBay Photo Digitization</CardTitle>
          <CardDescription>Analog slide scanner with AI enhancement</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <div>
            <h3 className="font-semibold text-foreground mb-2">Features</h3>
            <ul className="list-disc list-inside space-y-1">
              <li>Real-time WebSocket monitoring</li>
              <li>EXIF-based intelligent file naming</li>
              <li>CLAHE contrast enhancement</li>
              <li>Duplicate detection</li>
              <li>Auto-quality presets</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-2">Workflow</h3>
            <ol className="list-decimal list-inside space-y-1">
              <li>Place TIFFs in input/ directory</li>
              <li>Pipeline automatically processes files</li>
              <li>Enhanced JPEGs saved to enhanced_output/</li>
              <li>Monitor progress in real-time</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
