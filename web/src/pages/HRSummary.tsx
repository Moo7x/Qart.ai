export default function HRSummary() {
  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">HR summary</h1>
        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium">Aggregates only</span>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-sm text-amber-800">
        <strong>Privacy note:</strong> Individual recommendations are visible only to each employee.
        Groups smaller than 5 are suppressed. The system never makes promotion or dismissal decisions.
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-400">
        <div className="text-4xl mb-3">📊</div>
        <p className="font-medium text-gray-600">HR aggregate view</p>
        <p className="text-sm mt-1">Skill readiness counts and training demand will appear here after the engine is connected at M1.</p>
      </div>
    </div>
  )
}
