import { type FormEvent, useState } from "react"
import { GraduationCap, Plus } from "lucide-react"
import toast from "react-hot-toast"
import { useFetch } from "../hooks/useFetch"
import { api, getErrorMessage } from "../lib/api"
import { useAuthStore } from "../store/auth"
import { PageHeader } from "../components/ui/PageHeader"
import { Button } from "../components/ui/Button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card"
import { Field, Input } from "../components/ui/Input"
import { Select } from "../components/ui/Select"
import { Modal } from "../components/ui/Modal"
import { DataTable, type Column } from "../components/ui/Table"
import { EmptyState } from "../components/ui/EmptyState"
import { Skeleton } from "../components/ui/Skeleton"
import { Tabs } from "../components/ui/Tabs"
import { formatDate, fullName, gradeCellClasses, gradeColor } from "../lib/format"
import type {
  AcademicYear,
  ClassRoom,
  Grade,
  Paginated,
  Quarter,
  StudentProfile,
  Subject,
} from "../types"

export default function GradesPage() {
  const user = useAuthStore((s) => s.user)
  const isStaffOrTeacher = user?.role === "ADMIN" || user?.role === "SUPERADMIN" || user?.role === "TEACHER"
  return isStaffOrTeacher ? <ManageGradesView /> : <MyGradesView />
}

/* ------------------------------ Student/Parent ------------------------------- */

function MyGradesView() {
  const { data: students } = useFetch<Paginated<StudentProfile>>("/students/")
  const [activeChild, setActiveChild] = useState<number | null>(null)

  const children = students?.results ?? []
  const selectedId = activeChild ?? children[0]?.id ?? null

  return (
    <div>
      <PageHeader title="Baholar" description="Fanlar bo'yicha baholar va yillik natijalar" />

      {children.length > 1 && (
        <div className="mb-4">
          <Tabs
            tabs={children.map((c) => ({ key: String(c.id), label: fullName(c.user) }))}
            active={String(selectedId)}
            onChange={(k) => setActiveChild(Number(k))}
          />
        </div>
      )}

      {selectedId && <StudentGradeDetail studentId={selectedId} />}
    </div>
  )
}

interface AnnualSubjectResult {
  subject: number
  subject_name: string
  quarter_averages: Record<string, number>
  annual_average: number
}

function StudentGradeDetail({ studentId }: { studentId: number }) {
  const { data: years } = useFetch<Paginated<AcademicYear>>("/classes/academic-years/?page_size=1&is_active=true")
  const activeYear = years?.results[0]

  const { data: annual, loading: annualLoading } = useFetch<{ results: AnnualSubjectResult[] }>(
    activeYear ? `/grades/annual/?student=${studentId}&academic_year=${activeYear.id}` : null,
    [studentId, activeYear?.id]
  )
  const { data: recent, loading: recentLoading } = useFetch<Paginated<Grade>>(
    `/grades/?student=${studentId}&ordering=-created_at&page_size=10`,
    [studentId]
  )

  const columns: Column<Grade>[] = [
    { key: "subject", header: "Fan", render: (r) => r.subject_name },
    { key: "quarter", header: "Chorak", render: (r) => `${r.quarter}-chorak` },
    { key: "type", header: "Turi", render: (r) => r.grade_type, hideOnMobile: true },
    {
      key: "value",
      header: "Baho",
      render: (r) => <span className={`font-display text-base font-bold ${gradeColor(r.value)}`}>{r.value}</span>,
    },
    { key: "date", header: "Sana", render: (r) => formatDate(r.created_at), hideOnMobile: true },
  ]

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Choraklik baholar</CardTitle>
        </CardHeader>
        <CardContent>
          {annualLoading ? (
            <Skeleton className="h-56 w-full" />
          ) : !annual || annual.results.length === 0 ? (
            <EmptyState icon={GraduationCap} title="Hali baho yo'q" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] border-separate border-spacing-1.5 text-sm">
                <thead>
                  <tr>
                    <th className="px-2 pb-1 text-left text-xs font-semibold uppercase tracking-wide text-ink-400">Fan</th>
                    {[1, 2, 3, 4].map((q) => (
                      <th key={q} className="pb-1 text-center text-xs font-semibold uppercase tracking-wide text-ink-400">
                        {q}-chorak
                      </th>
                    ))}
                    <th className="pb-1 text-center text-xs font-semibold uppercase tracking-wide text-brand-500">Natija</th>
                  </tr>
                </thead>
                <tbody>
                  {annual.results.map((row) => (
                    <tr key={row.subject}>
                      <td className="px-2 py-1 text-sm font-medium text-ink-800 dark:text-ink-100">{row.subject_name}</td>
                      {[1, 2, 3, 4].map((q) => {
                        const value = row.quarter_averages[String(q)] ?? null
                        return (
                          <td key={q} className="p-0 text-center">
                            <div className={`mx-auto flex h-10 w-10 items-center justify-center rounded-lg font-display text-sm font-bold ${gradeCellClasses(value)}`}>
                              {value ?? "–"}
                            </div>
                          </td>
                        )
                      })}
                      <td className="p-0 text-center">
                        <div className={`mx-auto flex h-10 w-12 items-center justify-center rounded-lg font-display text-sm font-bold ring-2 ring-brand-400/40 ${gradeCellClasses(row.annual_average)}`}>
                          {row.annual_average}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>So'nggi baholar</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} rows={recent?.results ?? []} keyField={(r) => r.id} loading={recentLoading} emptyTitle="Baho yo'q" />
        </CardContent>
      </Card>
    </div>
  )
}

/* --------------------------------- Teacher/Admin --------------------------------- */

function ManageGradesView() {
  const [subjectFilter, setSubjectFilter] = useState("")
  const [addOpen, setAddOpen] = useState(false)

  const query = new URLSearchParams({ page_size: "50", ordering: "-created_at" })
  if (subjectFilter) query.set("subject", subjectFilter)

  const { data: subjects } = useFetch<Paginated<Subject>>("/subjects/?page_size=100")
  const { data: grades, loading, refetch } = useFetch<Paginated<Grade>>(`/grades/?${query.toString()}`, [subjectFilter])

  const columns: Column<Grade>[] = [
    { key: "student", header: "O'quvchi", render: (r) => r.student_name },
    { key: "subject", header: "Fan", render: (r) => r.subject_name },
    { key: "quarter", header: "Chorak", render: (r) => `${r.quarter}-chorak`, hideOnMobile: true },
    { key: "type", header: "Turi", render: (r) => r.grade_type, hideOnMobile: true },
    {
      key: "value",
      header: "Baho",
      render: (r) => <span className={`font-display text-base font-bold ${gradeColor(r.value)}`}>{r.value}</span>,
    },
    { key: "date", header: "Sana", render: (r) => formatDate(r.created_at), hideOnMobile: true },
  ]

  return (
    <div>
      <PageHeader
        title="Baholar"
        description="O'quvchilarga baho qo'yish va nazorat qilish"
        actions={
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Baho qo'yish
          </Button>
        }
      />

      <div className="mb-4 max-w-xs">
        <Select value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)}>
          <option value="">Barcha fanlar</option>
          {subjects?.results.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
      </div>

      <DataTable columns={columns} rows={grades?.results ?? []} keyField={(r) => r.id} loading={loading} emptyTitle="Baho topilmadi" />

      <AddGradeModal open={addOpen} onClose={() => setAddOpen(false)} onDone={() => { setAddOpen(false); refetch() }} />
    </div>
  )
}

function AddGradeModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const { data: classes } = useFetch<Paginated<ClassRoom>>(open ? "/classes/?page_size=100" : null)
  const { data: subjects } = useFetch<Paginated<Subject>>(open ? "/subjects/?page_size=100" : null)
  const { data: years } = useFetch<Paginated<AcademicYear>>(open ? "/classes/academic-years/?page_size=100" : null)

  const [classRoom, setClassRoom] = useState("")
  const { data: students } = useFetch<Paginated<StudentProfile>>(classRoom ? `/students/?class_room=${classRoom}&page_size=100` : null, [classRoom])
  const [academicYear, setAcademicYear] = useState("")
  const { data: quarters } = useFetch<Paginated<Quarter>>(academicYear ? `/classes/quarters/?academic_year=${academicYear}` : null, [academicYear])

  const [form, setForm] = useState({ student: "", subject: "", quarter: "", value: "", grade_type: "DAILY", comment: "" })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post("/grades/", { ...form, academic_year: academicYear })
      toast.success("Baho qo'yildi")
      setForm({ student: "", subject: "", quarter: "", value: "", grade_type: "DAILY", comment: "" })
      onDone()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Baho qo'yish" size="lg">
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Sinf">
          <Select value={classRoom} onChange={(e) => setClassRoom(e.target.value)} required>
            <option value="">Tanlang...</option>
            {classes?.results.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="O'quvchi">
          <Select value={form.student} onChange={(e) => setForm((f) => ({ ...f, student: e.target.value }))} required disabled={!classRoom}>
            <option value="">Tanlang...</option>
            {students?.results.map((s) => (
              <option key={s.id} value={s.id}>
                {fullName(s.user)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Fan">
          <Select value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} required>
            <option value="">Tanlang...</option>
            {subjects?.results.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="O'quv yili">
          <Select value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} required>
            <option value="">Tanlang...</option>
            {years?.results.map((y) => (
              <option key={y.id} value={y.id}>
                {y.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Chorak">
          <Select value={form.quarter} onChange={(e) => setForm((f) => ({ ...f, quarter: e.target.value }))} required disabled={!academicYear}>
            <option value="">Tanlang...</option>
            {quarters?.results.map((q) => (
              <option key={q.id} value={q.id}>
                {q.number}-chorak
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Baho turi">
          <Select value={form.grade_type} onChange={(e) => setForm((f) => ({ ...f, grade_type: e.target.value }))}>
            <option value="DAILY">Kundalik</option>
            <option value="HOMEWORK">Uy vazifasi</option>
            <option value="QUIZ">Test</option>
            <option value="QUARTER">Chorak</option>
            <option value="EXAM">Imtihon</option>
          </Select>
        </Field>
        <Field label="Baho (0-10)">
          <Input type="number" min={0} max={10} value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} required />
        </Field>
        <Field label="Izoh">
          <Input value={form.comment} onChange={(e) => setForm((f) => ({ ...f, comment: e.target.value }))} />
        </Field>
        <Button type="submit" className="sm:col-span-2" loading={loading}>
          Saqlash
        </Button>
      </form>
    </Modal>
  )
}
