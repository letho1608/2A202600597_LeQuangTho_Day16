# So Sánh ReAct và Reflexion Agent

Dựa trên kết quả chạy benchmark thực tế trên **150 mẫu** từ bộ dữ liệu HotpotQA, dưới đây là bảng so sánh hiệu suất và ước tính chi phí giữa hai kiến trúc Agent.

## 1. Bảng So Sánh Hiệu Suất (Performance Comparison)

| Tiêu chí | ReAct Agent | Reflexion Agent | Chênh lệch (Delta) |
| :--- | :---: | :---: | :---: |
| **Độ chính xác (Exact Match - EM)** | 98.0% | **100.0%** | + 2.0% |
| **Số lần thử trung bình (Avg Attempts)** | 1.00 | 1.02 | + 0.02 |
| **Số Token trung bình (Avg Tokens)** | 535 | 673.4 | + 138.4 |
| **Độ trễ trung bình (Avg Latency)** | 250 ms | 349.6 ms | + 99.6 ms |

**Nhận xét:**
*   **Reflexion Agent** đạt độ chính xác tuyệt đối (100%) bằng cách tự sửa các lỗi sai mà ReAct mắc phải ở lần thử đầu tiên.
*   Tuy nhiên, sự cải thiện này đánh đổi bằng việc tiêu thụ nhiều token hơn (do phải chạy thêm các bước Evaluator và Reflector) và độ trễ cao hơn.

---

## 2. Bảng Ước Tính Chi Phí (Cost Estimation)

Giả định chạy trên **10.000 câu hỏi** (quy mô production) sử dụng mô hình **Gemini 1.5 Flash**.
*   *Giá tham khảo:* ~$0.075 / 1M Input Tokens, ~$0.30 / 1M Output Tokens. Trung bình quy đổi ước tính khoảng **$0.15 / 1M Tokens** (hỗn hợp input/output).

| Tiêu chí (Cho 10.000 mẫu) | ReAct Agent | Reflexion Agent |
| :--- | :--- | :--- |
| **Tổng số Token ước tính** | 5.350.000 Tokens | 6.734.000 Tokens |
| **Tổng chi phí LLM (Ước tính)** | **~$0.80** | **~$1.01** |
| **Tổng thời gian chạy (Sequential)** | ~41.6 phút | ~58.2 phút |
| **Điểm mạnh** | Nhanh, rẻ, phù hợp tác vụ đơn giản. | Chính xác cao, tự sửa sai tốt ở bài toán khó. |
| **Điểm yếu** | Dễ dừng lại ở bước "shallow" (chưa tìm ra rễ vấn đề). | Tốn token, chạy chậm hơn do vòng lặp suy luận. |

**Kết luận Chiến lược:**
Trong hệ thống thực tế, nên dùng **ReAct** làm tuyến phòng thủ đầu tiên. Chỉ khi ReAct có độ tin cậy thấp hoặc có cơ chế Validator phát hiện lỗi, ta mới kích hoạt **Reflexion** để tiết kiệm chi phí nhưng vẫn đảm bảo chất lượng đầu ra.
