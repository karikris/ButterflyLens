import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import './design-system/foundations.css'
import './design-system/primitives.css'
import './shell/publicShell.css'
import './species/speciesDirectory.css'
import './flickr/flickrDisplayBoundary.css'
import './community/contributorExperience.css'
import './analyst/askButterflyLens.css'
import './operations/operationsDashboard.css'
import './map/submittedEvidenceMap.css'
import './styles.css'

const root = document.getElementById('root')

if (root === null) {
  throw new Error('ButterflyLens root element is missing')
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
