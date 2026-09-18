// FR-3: set password after OTP verification (min 8 chars, 1 number, 1 special char).
export default function SetPassword() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form className="w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">Set a password</h1>
        {/* TODO: password + confirm password fields with client-side strength check */}
      </form>
    </div>
  )
}
