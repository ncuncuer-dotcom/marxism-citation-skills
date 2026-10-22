import Foundation
import PDFKit
import Vision
import AppKit
import CryptoKit
let args = CommandLine.arguments
if args.count != 3 { fatalError("Usage: ocr_macos.swift source.pdf output.jsonl") }
let source = URL(fileURLWithPath: args[1])
let output = URL(fileURLWithPath: args[2])
let digest = SHA256.hash(data: try Data(contentsOf: source)).map { String(format: "%02x", $0) }.joined()
guard let doc = PDFDocument(url: source) else { fatalError("Cannot read PDF") }
var done = Set<Int>()
if FileManager.default.fileExists(atPath: output.path) {
 let contents = try String(contentsOf: output, encoding: .utf8)
 for line in contents.split(separator: "\n") {
  guard let data = line.data(using: .utf8), let row = try JSONSerialization.jsonObject(with: data) as? [String:Any] else { fatalError("Invalid JSONL") }
  guard row["sha256"] as? String == digest else { fatalError("Source fingerprint mismatch") }
  if let page = row["pdf_page"] as? Int { done.insert(page) }
 }
} else { FileManager.default.createFile(atPath: output.path, contents: nil) }
let handle = try FileHandle(forWritingTo: output)
try handle.seekToEnd()
for i in 0..<doc.pageCount {
 if done.contains(i+1) { continue }
 try autoreleasepool {
  guard let page = doc.page(at: i) else { fatalError("Missing page") }
  let bounds = page.bounds(for: .mediaBox)
  let width: CGFloat = 1300
  let image = page.thumbnail(of: NSSize(width: width, height: width*bounds.height/bounds.width), for: .mediaBox)
  var rect = NSRect(origin: .zero, size: image.size)
  guard let cg = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { fatalError("Cannot render page") }
  let request = VNRecognizeTextRequest()
  request.recognitionLevel = .accurate
  request.recognitionLanguages = ["zh-Hans", "en-US"]
  request.usesLanguageCorrection = true
  try VNImageRequestHandler(cgImage: cg).perform([request])
  let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
  let row: [String:Any] = ["pdf_page":i+1,"text":text,"sha256":digest,"engine":"Apple Vision accurate zh-Hans"]
  var data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
  data.append(10)
  try handle.write(contentsOf:data)
 }
 if (i+1)%25 == 0 { print("OCR \(i+1)/\(doc.pageCount)"); fflush(stdout) }
}
try handle.close()
print("OCR completed \(doc.pageCount) pages")
