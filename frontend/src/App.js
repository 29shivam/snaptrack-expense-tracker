import { AnimatePresence, motion } from "framer-motion";
import React, { useEffect, useState } from "react";

const API_URL = "https://ze18ti6uua.execute-api.us-east-2.amazonaws.com/prod/expenses";


function App() {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  // Fetch expenses
  useEffect(() => {
    setLoading(true);
    fetch(API_URL)
      .then(res => res.json())
      .then(data => {
        setExpenses(data);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-cyan-100 to-blue-200 flex flex-col items-center py-10">
      <motion.h1 
        className="text-4xl font-bold mb-4 text-cyan-700 drop-shadow-lg"
        initial={{ y: -40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
      >
        SnapTrack: Your Receipts, Instantly Organized
      </motion.h1>
      <motion.p 
        className="mb-10 text-gray-600 text-center max-w-2xl"
        initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.3 } }}
      >
        View your uploaded receipts as automatically extracted, organized expenses. 
        (For uploads, please use the AWS S3 Console for now.)
      </motion.p>
      <div className="w-full max-w-4xl rounded-2xl shadow-2xl bg-white p-8">
        <h2 className="text-2xl font-semibold mb-6 text-blue-600 flex items-center gap-2">
          <span>Expenses</span>
          {loading && (
            <svg className="animate-spin w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
          )}
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-cyan-100">
                <th className="py-2 px-3 text-left rounded-tl-2xl">Vendor</th>
                <th className="py-2 px-3 text-left">Date</th>
                <th className="py-2 px-3 text-left">Total</th>
                <th className="py-2 px-3 text-left">Line Items</th>
                <th className="py-2 px-3 text-left rounded-tr-2xl"></th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {!loading && expenses.map((exp, i) => (
                  <motion.tr 
                    key={exp.ExpenseId || i}
                    className="hover:bg-cyan-50 transition"
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                  >
                    <td className="py-2 px-3 font-medium">{exp.Vendor}</td>
                    <td className="py-2 px-3">{exp.Date?.slice(0,10) || "—"}</td>
                    <td className="py-2 px-3">${Number(exp.Total).toFixed(2)}</td>
                    <td className="py-2 px-3">
                      <ul className="text-xs">
                        {exp.LineItems?.length > 0 ? (
                          exp.LineItems.map((li, j) => (
                            <li key={j} className="mb-1">
                              <span className="font-semibold">{li.Description}</span>
                              <span className="ml-2 text-cyan-700">${li.Amount}</span>
                            </li>
                          ))
                        ) : <span className="text-gray-400 italic">—</span>}
                      </ul>
                    </td>
                    <td className="py-2 px-3">
                      <button
                        className="text-blue-500 underline"
                        onClick={() => setSelected(exp)}
                      >Details</button>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
          {!loading && expenses.length === 0 && (
            <div className="text-gray-400 italic text-center py-10">No expenses found.</div>
          )}
        </div>
      </div>

      {/* Details Modal */}
      <AnimatePresence>
        {selected && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center bg-black/50"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setSelected(null)}
          >
            <motion.div
              className="bg-white rounded-2xl shadow-2xl p-8 w-[95vw] max-w-lg"
              initial={{ scale: 0.8 }} animate={{ scale: 1 }} exit={{ scale: 0.8 }}
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-2 text-cyan-700">Expense Details</h3>
              <div className="mb-2"><b>Vendor:</b> {selected.Vendor}</div>
              <div className="mb-2"><b>Date:</b> {selected.Date?.slice(0,10)}</div>
              <div className="mb-2"><b>Total:</b> ${Number(selected.Total).toFixed(2)}</div>
              <div className="mb-2"><b>Receipt S3 Path:</b> <span className="break-all">{selected.ReceiptS3Path}</span></div>
              <div className="mb-2"><b>Created At:</b> {selected.CreatedAt?.slice(0,19).replace('T',' ')}</div>
              <div><b>Line Items:</b>
                <ul className="ml-4 mt-1 list-disc">
                  {selected.LineItems?.length > 0 ? (
                    selected.LineItems.map((li, j) => (
                      <li key={j}>{li.Description} <b>${li.Amount}</b></li>
                    ))
                  ) : <span className="text-gray-400 italic">None</span>}
                </ul>
              </div>
              <button
                className="mt-6 bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-xl transition"
                onClick={() => setSelected(null)}
              >Close</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
