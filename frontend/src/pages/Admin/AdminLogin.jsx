// FR-7.1: admin login served at a non-public path, isolated session from students.
export default function AdminLogin() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form className="w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">Admin Login</h1>
        {/* TODO: email + password fields */}
      </form>
    </div>
  )
}
