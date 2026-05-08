"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  GraduationCap,
  Upload,
  Clock,
  Code2,
  FileUp,
  Activity,
  Trash2,
  RefreshCw,
  Search,
  Check,
  FileText,
  Download,
  AlertCircle,
  XCircle,
  CheckCircle2,
  Brain,
  ChevronDown
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import toast, { Toaster } from "react-hot-toast";
import { useDropzone, type FileRejection } from "react-dropzone";

const API_BASE = "http://127.0.0.1:8000";
const TOAST_DURATION_MS = 4000;

// ==================== TYPES ====================
interface StudentInfo {
  id: string;
  name: string;
}

interface GradingResult {
  id: number;
  student_id: string;
  student_name: string;
  assignment_code: string;
  filename: string;
  topic: string;
  total_score: number;
  final_score: number;
  status: string;
  code: string;
  algorithms_detected?: string[];
  feedback?: string;
  ai_advice?: string;
  submitted_at: string;
  test_runs?: TestRun[];
}

interface TestRun {
  test_id: string;
  passed: boolean;
  stdout: string;
  stderr: string;
  time_ms: number;
  memory_kb: number;
  input?: string;
  expected?: string;
}

type TabId = "submit" | "results";

// ==================== GRADING OVERLAY ====================
const GradingOverlay = ({ progress, step }: { progress: number; step: string }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-[100] bg-slate-900/40 backdrop-blur-sm flex flex-col items-center justify-center p-6"
  >
    <motion.div 
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="bg-white rounded-[24px] p-10 shadow-xl max-w-sm w-full flex flex-col items-center text-center"
    >
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-2xl bg-blue-50 flex items-center justify-center relative overflow-hidden">
          <RefreshCw className="w-10 h-10 text-[#1b5eab] animate-spin" />
        </div>
      </div>
      
      <h3 className="text-3xl font-bold mb-2 text-slate-900 tabular-nums">{progress}%</h3>
      <p className="text-xs font-bold text-slate-400 mb-6 uppercase tracking-[0.2em]">{step}</p>
      
      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-4">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }} 
          className="h-full bg-[#1b5eab] rounded-full" 
        />
      </div>
      <p className="text-[11px] text-slate-400 font-medium italic">Hệ thống đang xử lý bài nộp thuật toán của bạn...</p>
    </motion.div>
  </motion.div>
);

// ==================== MAIN PAGE ====================
export default function StudentPage() {
  const [activeTab, setActiveTab] = useState<TabId>("submit");
  const [studentInfo, setStudentInfo] = useState<StudentInfo>({ id: "", name: "" });
  const [files, setFiles] = useState<File[]>([]);
  const [resultsHistory, setResultsHistory] = useState<GradingResult[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitProgress, setSubmitProgress] = useState(0);
  const [submitStep, setSubmitStep] = useState("");
  const [expandedFileId, setExpandedFileId] = useState<number | null>(null);

  // Load persisted data
  useEffect(() => {
    const saved = localStorage.getItem("edu_results_v10");
    const savedStudent = localStorage.getItem("edu_student_v2");

    if (saved) {
      try { setResultsHistory(JSON.parse(saved)); } catch {}
    }
    if (savedStudent) {
      try { setStudentInfo(JSON.parse(savedStudent)); } catch {}
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("edu_results_v10", JSON.stringify(resultsHistory));
  }, [resultsHistory]);

  useEffect(() => {
    localStorage.setItem("edu_student_v2", JSON.stringify(studentInfo));
  }, [studentInfo]);

  // ==================== HANDLERS ====================
  const notify = useCallback((type: "success" | "error", message: string) => {
    type === "success" ? toast.success(message) : toast.error(message);
  }, []);

  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    if (rejected.length > 0) {
      toast.error("Tệp không hợp lệ. Chỉ chấp nhận .py, .zip, .rar.");
    }
    if (accepted.length === 0) return;
    setFiles(prev => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 
      "text/x-python": [".py"], 
      "application/zip": [".zip"], 
      "application/x-rar-compressed": [".rar"],
      "application/x-zip-compressed": [".zip"]
    },
    maxSize: 100 * 1024 * 1024, // 100MB per image info
  });

  const handleSubmit = async () => {
    if (!studentInfo.id.trim() || !studentInfo.name.trim()) {
      notify("error", "Vui lòng nhập đầy đủ MSSV và họ tên.");
      return;
    }
    if (files.length === 0) {
      notify("error", "Vui lòng chọn ít nhất một tệp để nộp.");
      return;
    }

    setIsSubmitting(true);
    setSubmitProgress(0);
    setSubmitStep("Khởi tạo...");

    try {
      setSubmitProgress(10);
      setSubmitStep("Gửi mã nguồn...");

      const formData = new FormData();
      formData.append("student_id", studentInfo.id);
      formData.append("student_name", studentInfo.name);
      files.forEach(file => formData.append("files", file));

      const res = await fetch(`${API_BASE}/api/grade`, { method: "POST", body: formData });

      if (!res.ok) throw new Error("Gửi bài thất bại");

      setSubmitProgress(30);
      setSubmitStep("Xếp hàng chấm điểm...");

      const data = await res.json();
      const jobId = data.job_id;

      if (!jobId) {
          // If immediate result returned
          if (data.results) {
              setResultsHistory(prev => [...data.results, ...prev]);
              notify("success", "Chấm điểm hoàn tất!");
              setFiles([]);
              return;
          }
          throw new Error("Không nhận được mã phiên chấm.");
      }

      // Poll for results
      let attempts = 0;
      const maxAttempts = 60;
      while (attempts < maxAttempts) {
        await new Promise(r => setTimeout(r, 2000));
        setSubmitProgress(30 + Math.min(65, attempts * 2));
        setSubmitStep("Đang phân tích & chấm điểm...");

        const statusRes = await fetch(`${API_BASE}/api/job/${jobId}`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.status === "completed") {
            setSubmitProgress(100);
            setSubmitStep("Hoàn thành!");

            if (statusData.results) {
               setResultsHistory(prev => [...statusData.results, ...prev]);
            }
            
            notify("success", "Chấm điểm hoàn tất!");
            setFiles([]);
            break;
          } else if (statusData.status === "failed") {
            throw new Error(statusData.error || "Chấm điểm thất bại");
          }
        }
        attempts++;
      }
      
      if (attempts >= maxAttempts) throw new Error("Hết thời gian chờ chấm điểm.");

    } catch (error: any) {
      notify("error", error.message || "Có lỗi xảy ra");
    } finally {
      setTimeout(() => { setIsSubmitting(false); setSubmitProgress(0); setSubmitStep(""); }, 1000);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearHistory = () => {
    if (confirm("Xóa toàn bộ lịch sử kết quả?")) {
        setResultsHistory([]);
        setExpandedFileId(null);
    }
  };

  // ==================== COMPUTED ====================
  const avgScore = resultsHistory.length > 0 ? (resultsHistory.reduce((a, r) => a + (r.final_score ?? r.total_score ?? 0), 0) / resultsHistory.length).toFixed(1) : "0.0";
  const totalSubmissions = resultsHistory.length;

  // ==================== RENDER ====================
  return (
    <div className="min-h-screen bg-[#f4f7fa] flex flex-col font-sans selection:bg-blue-100 italic:text-blue-900 overflow-hidden">
      <Toaster position="top-right" toastOptions={{ duration: TOAST_DURATION_MS }} />
      <AnimatePresence>{isSubmitting && <GradingOverlay progress={submitProgress} step={submitStep} />}</AnimatePresence>

      {/* ===== GLOBAL HEADER ===== */}
      <header className="header shrink-0 z-50 sticky top-0 shadow-sm flex items-center justify-between px-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center shrink-0 border border-white/20">
            <GraduationCap className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight uppercase text-white">Hệ thống tra cứu điểm thi</h1>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => setActiveTab("submit")}
            className={`btn-nav ${activeTab === "submit" ? "active" : ""}`}
          >
            <FileUp className="w-4 h-4" />
            <span>Quy chế nộp bài</span>
          </button>
          <button 
            onClick={() => setActiveTab("results")}
            className={`btn-nav ${activeTab === "results" ? "active" : ""}`}
          >
            <Activity className="w-4 h-4" />
            <span>Kết quả</span>
          </button>
        </div>
      </header>

      {/* ===== MAIN CONTENT ===== */}
      <main className="flex-1 overflow-y-auto py-10 px-4">
        <div className="max-w-4xl mx-auto">

          {/* ===== SUBMIT TAB ===== */}
          {activeTab === "submit" && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6 pb-20"
            >
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-slate-800">Nộp bài tập thực hành</h2>
                <p className="text-sm text-slate-500 mt-1">Điền mã số sinh viên, họ tên và đính kèm file theo đúng định dạng được yêu cầu.</p>
              </div>

              {/* Step 1: Info */}
              <div className="card overflow-hidden">
                <div className="flex items-center gap-3 p-5 bg-slate-50/50 border-b border-slate-100">
                  <div className="step-number">1</div>
                  <h3 className="font-bold text-slate-700">Thông tin sinh viên</h3>
                </div>
                <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Mã số sinh viên <span className="text-red-500">*</span></label>
                    <input
                      type="text"
                      value={studentInfo.id}
                      onChange={e => setStudentInfo(prev => ({ ...prev, id: e.target.value }))}
                      placeholder="Ví dụ: 122000000"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Họ và tên <span className="text-red-500">*</span></label>
                    <input
                      type="text"
                      value={studentInfo.name}
                      onChange={e => setStudentInfo(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Ví dụ: Nguyễn Văn A"
                      className="input"
                    />
                  </div>
                </div>
              </div>

              {/* Step 2: Upload */}
              <div className="card overflow-hidden">
                <div className="flex items-center gap-3 p-5 bg-slate-50/50 border-b border-slate-100">
                  <div className="step-number">2</div>
                  <h3 className="font-bold text-slate-700">Chọn bài làm tải lên</h3>
                  <div className="ml-auto flex gap-1">
                      <span className="text-[9px] bg-slate-500 text-white px-1.5 py-0.5 rounded font-black">.PY</span>
                      <span className="text-[9px] bg-slate-500 text-white px-1.5 py-0.5 rounded font-black">.ZIP</span>
                      <span className="text-[9px] bg-slate-500 text-white px-1.5 py-0.5 rounded font-black">.RAR</span>
                  </div>
                </div>
                <div className="p-8">
                   <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-all ${
                      isDragActive ? "border-[#1b5eab] bg-blue-50/30" : "border-slate-200 hover:border-[#1b5eab]"
                    }`}
                  >
                    <input {...getInputProps()} />
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-5 shadow-inner">
                      <Upload className="w-7 h-7 text-slate-400" />
                    </div>
                    <p className="text-sm font-medium text-slate-700">Kéo thả tệp hoặc <span className="font-bold text-[#1b5eab]">nhấn để tải lên</span></p>
                    <p className="text-xs text-slate-400 mt-2 italic">Chỉ chấp nhận file dưới 100 MB</p>
                  </div>

                  {files.length > 0 && (
                    <div className="mt-6 space-y-2">
                       {files.map((file, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-100 rounded-lg">
                            <div className="flex items-center gap-3 overflow-hidden">
                              <FileText className="w-4 h-4 text-[#1b5eab] shrink-0" />
                              <span className="text-sm font-medium text-slate-900 truncate">{file.name}</span>
                              <span className="text-[10px] text-slate-400">({(file.size / 1024).toFixed(0)} KB)</span>
                            </div>
                            <button onClick={() => removeFile(i)} className="p-1 hover:bg-white rounded transition-colors text-slate-400 hover:text-red-500">
                                <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                       ))}
                    </div>
                  )}

                  <div className="mt-10 flex justify-center">
                    <button
                      onClick={handleSubmit}
                      disabled={isSubmitting}
                      className="bg-[#1b5eab] hover:bg-[#154b8a] text-white px-12 py-3.5 rounded-lg font-bold shadow-lg transition-all active:scale-95 disabled:opacity-50 flex items-center gap-3"
                    >
                      {isSubmitting ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            <span>Đang xử lý bài nộp...</span>
                          </>
                      ) : (
                          <span>Nộp bài và chấm điểm</span>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ===== RESULTS TAB ===== */}
          {activeTab === "results" && (
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-8"
            >
              <div className="flex items-center gap-3">
                 <div className="w-1 h-6 bg-[#1b5eab] rounded-full" />
                 <h2 className="text-xl font-bold text-slate-800 uppercase tracking-tight">Tổng quan phiên chấm điểm</h2>
              </div>

              {/* Summary Card */}
              <div className="card grid grid-cols-1 md:grid-cols-4 overflow-hidden">
                <div className="md:col-span-1 p-8 flex flex-col items-center justify-center border-b md:border-b-0 md:border-r border-slate-100 bg-slate-50/30">
                  <div className="w-16 h-16 rounded-full border-2 border-slate-100 flex items-center justify-center mb-4 bg-white shadow-sm">
                    <Code2 className="w-7 h-7 text-[#1b5eab]" />
                  </div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mã Phiên Chấm</p>
                  <p className="text-xl font-black text-[#1b5eab] mt-1 tabular-nums">#{(resultsHistory[0]?.id || 7295)}</p>
                  <span className="mt-3 badge-success">✓ Hoàn tất</span>
                </div>

                <div className="md:col-span-3 p-8 grid grid-cols-2 gap-y-10">
                  <div className="px-6 border-r border-slate-100">
                     <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">TỔNG SỐ BÀI NỘP</p>
                     <p className="text-2xl font-black text-slate-900 mt-1">{totalSubmissions} <span className="text-xs text-slate-400 font-bold ml-1">Bài</span></p>
                  </div>
                  <div className="px-6">
                     <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">ĐIỂM TRUNG BÌNH</p>
                     <p className="text-2xl font-black text-green-600 mt-1">{avgScore} <span className="text-xs text-slate-400 font-bold ml-1">/ 100</span></p>
                  </div>
                  <div className="px-6 border-r border-slate-100">
                     <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5"><Clock className="w-3 h-3" /> THỜI GIAN XỬ LÝ CPU</p>
                     <p className="text-2xl font-black text-slate-900 mt-1">0.0s</p>
                  </div>
                  <div className="px-6">
                     <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5"><Download className="w-3 h-3" /> LƯU TRỮ DỮ LIỆU</p>
                     <p className="text-2xl font-black text-slate-900 mt-1">{resultsHistory.length} <span className="text-xs text-slate-400 font-bold ml-1">bản ghi</span></p>
                  </div>
                </div>
              </div>

              {/* Filter Section */}
              <div className="card p-6 grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
                <div>
                  <label className="text-[11px] font-bold text-slate-500 block mb-2 px-1">Tìm kiếm bài nộp (Tên SV, file)</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input type="text" placeholder="Nhập từ khóa tìm kiếm..." className="input pl-10 h-11" />
                  </div>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-500 block mb-2 px-1">Trạng thái chấm</label>
                  <div className="relative">
                      <select className="input h-11 appearance-none bg-no-repeat bg-[right_12px_center] pr-10 cursor-pointer">
                        <option>Tất cả trạng thái</option>
                        <option>Chữa Đạt (Fail)</option>
                        <option>Hoàn thành (Success)</option>
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-1 h-6 bg-[#1b5eab] rounded-full" />
                    <h2 className="text-xl font-bold text-slate-800 uppercase tracking-tight">Chi tiết kết quả điểm thành phần</h2>
                  </div>
                  {resultsHistory.length > 0 && (
                      <button onClick={clearHistory} className="text-xs font-bold text-red-400 hover:text-red-500 flex items-center gap-1.5">
                          <Trash2 className="w-3.5 h-3.5" /> Xóa lịch sử
                      </button>
                  )}
              </div>

              {/* Details List */}
              <div className="space-y-4">
                {resultsHistory.length === 0 ? (
                    <div className="card p-24 flex flex-col items-center justify-center text-center">
                        <Search className="w-12 h-12 text-slate-100 mb-4" />
                        <p className="text-sm text-slate-400 font-bold max-w-[240px]">Không tìm thấy bài làm khớp với bộ lọc. Hãy thử tìm từ khóa khác.</p>
                    </div>
                ) : (
                    resultsHistory.map((result) => (
                        <div key={result.id} className="card overflow-hidden group hover:border-[#1b5eab]/30 transition-all">
                            <button
                                onClick={() => setExpandedFileId(expandedFileId === result.id ? null : result.id)}
                                className="w-full p-6 flex items-center justify-between text-left"
                            >
                                <div className="flex items-center gap-5">
                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg ${
                                        result.final_score >= 80 ? 'bg-green-50 text-green-600' :
                                        result.final_score >= 50 ? 'bg-orange-50 text-orange-600' :
                                        'bg-red-50 text-red-600'
                                    }`}>
                                        {result.final_score}
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-slate-900">{result.filename}</h4>
                                        <p className="text-xs text-slate-400 font-medium">MSSV: {result.student_id} • {new Date(result.submitted_at).toLocaleString()}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className={`px-2.5 py-1 rounded text-[10px] font-black uppercase ${result.status === 'AC' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
                                        {result.status}
                                    </span>
                                    <ChevronDown className={`w-5 h-5 text-slate-300 transition-transform ${expandedFileId === result.id ? 'rotate-180' : ''}`} />
                                </div>
                            </button>
                            
                            <AnimatePresence>
                                {expandedFileId === result.id && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="border-t border-slate-50 bg-slate-50/30 p-8"
                                    >
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                                            <div className="space-y-6">
                                                <div>
                                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Phản hồi hệ thống</p>
                                                    <div className="bg-white p-5 rounded-xl border border-slate-100 text-sm italic text-slate-600 leading-relaxed shadow-sm">
                                                        {result.feedback || "Không có phản hồi cụ thể."}
                                                    </div>
                                                </div>
                                                {result.algorithms_detected && (
                                                    <div>
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Thuật toán nhận diện</p>
                                                        <div className="flex flex-wrap gap-2">
                                                            {result.algorithms_detected.map((algo, i) => (
                                                                <span key={i} className="px-3 py-1 bg-blue-50 text-[#1b5eab] rounded-lg text-xs font-bold border border-blue-100">
                                                                    {algo}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                            
                                            {result.ai_advice && (
                                                <div className="bg-[#1b5eab] p-6 rounded-2xl text-white shadow-lg relative overflow-hidden">
                                                    <Brain className="absolute -right-4 -bottom-4 w-24 h-24 opacity-10" />
                                                    <p className="text-[10px] font-black text-white/50 uppercase tracking-widest mb-4 flex items-center gap-2">
                                                        <Brain className="w-3.5 h-3.5" /> AI Tư vấn cải thiện
                                                    </p>
                                                    <p className="text-sm font-bold leading-relaxed whitespace-pre-line">
                                                        {result.ai_advice}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    ))
                )}
              </div>
            </motion.div>
          )}
        </div>
      </main>
      
      {/* ===== ACTIONS DIALOG ===== */}
      {/* ... Simple confirmation dialog could be added here if needed ... */}
      
    </div>
  );
}
