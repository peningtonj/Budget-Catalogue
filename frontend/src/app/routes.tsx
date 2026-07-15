import { createBrowserRouter } from 'react-router-dom'

import App from './App'
import { CatalogueSearchPage } from '../features/catalogue/pages/CatalogueSearchPage'
import { ChatbotPage } from '../features/chatbot/pages/ChatbotPage'
import { MeasureDetailPage } from '../features/measures/pages/MeasureDetailPage'


export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <CatalogueSearchPage />,
      },
      {
        path: 'chat',
        element: <ChatbotPage />,
      },
      {
        path: 'measures/:measureId',
        element: <MeasureDetailPage />,
      },
    ],
  },
])
