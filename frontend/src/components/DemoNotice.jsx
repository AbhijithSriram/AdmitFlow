import { Link } from 'react-router-dom'
import { DEMO_NOTICE } from '../content/institution'
import { useContent } from '../context/ContentContext'

// Bars above every page (student and staff):
// - while the deployment is in demo mode (a server setting, not editable by admins), the
//   academic-project notice, so nobody mistakes this site for a real college's portal;
// - if the site content could not be loaded, a warning that pages may be incomplete.
export default function DemoNotice() {
  const { content, loadFailed } = useContent()
  return (
    <>
      {loadFailed && (
        <div role="alert" className="bg-red-100 text-red-900 text-sm px-4 py-2 text-center border-b border-red-300">
          The site&rsquo;s content could not be loaded, so some pages may be incomplete. Please refresh in a moment.
        </div>
      )}
      {content.demo_mode && (
        <div role="note" className="bg-amber-100 text-amber-950 text-xs sm:text-sm px-4 py-2 text-center border-b border-amber-300">
          {DEMO_NOTICE}{' '}
          <Link to="/info/about" className="underline font-medium whitespace-nowrap">
            About this project
          </Link>
        </div>
      )}
    </>
  )
}
