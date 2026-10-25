import { Link } from 'react-router-dom'
import { DEMO_NOTICE } from '../content/institution'

// A thin bar above every page (student and staff): this public site is an academic project, so nobody
// should mistake it for a real college's admissions portal. Not dismissible on purpose.
export default function DemoNotice() {
  return (
    <div role="note" className="bg-amber-100 text-amber-950 text-xs sm:text-sm px-4 py-2 text-center border-b border-amber-300">
      {DEMO_NOTICE}{' '}
      <Link to="/info/about" className="underline font-medium whitespace-nowrap">
        About this project
      </Link>
    </div>
  )
}
