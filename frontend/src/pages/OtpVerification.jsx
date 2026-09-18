// FR-3: OTP verification — 6-digit code, 10-minute expiry, then password setup.
export default function OtpVerification() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form className="w-full max-w-sm flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">Verify your email</h1>
        {/* TODO: 6-digit OTP input + resend action */}
      </form>
    </div>
  )
}
