import java.io.*;
import java.net.*;
import java.nio.file.Files;
import java.util.UUID;

public class EmulatorProbe {
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("Usage: EmulatorProbe <GET|POST> <URL> [image_path]");
            return;
        }

        String method = args[0].toUpperCase();
        String urlString = args.length > 1 ? args[1] : "http://10.0.2.2:8000/health";

        System.out.println("=== AgriMind Android Emulator Live Probe ===");
        System.out.println("Target URL: " + urlString);
        System.out.println("Method:     " + method);

        try {
            if ("GET".equals(method)) {
                executeGet(urlString);
            } else if ("POST".equals(method)) {
                String imagePath = args.length > 2 ? args[2] : null;
                executePost(urlString, imagePath);
            } else {
                System.out.println("Unsupported method: " + method);
            }
        } catch (Exception e) {
            System.out.println("PROBE_EXCEPTION: " + e.getClass().getName() + " - " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static void executeGet(String urlString) throws Exception {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);

        int status = conn.getResponseCode();
        System.out.println("HTTP_STATUS: " + status);

        InputStream is = (status >= 200 && status < 400) ? conn.getInputStream() : conn.getErrorStream();
        BufferedReader reader = new BufferedReader(new InputStreamReader(is));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        reader.close();
        System.out.println("HTTP_RESPONSE: " + sb.toString());
    }

    private static void executePost(String urlString, String imagePath) throws Exception {
        String boundary = "===" + System.currentTimeMillis() + "===";
        String lineEnd = "\r\n";
        String twoHyphens = "--";

        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setDoOutput(true);
        conn.setDoInput(true);
        conn.setUseCaches(false);
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Connection", "Keep-Alive");
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(90000); // Allow sufficient time for neural network inference

        DataOutputStream dos = new DataOutputStream(conn.getOutputStream());

        // Field 1: leaf_damage_percentage
        dos.writeBytes(twoHyphens + boundary + lineEnd);
        dos.writeBytes("Content-Disposition: form-data; name=\"leaf_damage_percentage\"" + lineEnd + lineEnd);
        dos.writeBytes("14.0" + lineEnd);

        // Field 2: canopy_spread
        dos.writeBytes(twoHyphens + boundary + lineEnd);
        dos.writeBytes("Content-Disposition: form-data; name=\"canopy_spread\"" + lineEnd + lineEnd);
        dos.writeBytes("lower_canopy" + lineEnd);

        // File: file
        if (imagePath != null && new File(imagePath).exists()) {
            File f = new File(imagePath);
            dos.writeBytes(twoHyphens + boundary + lineEnd);
            dos.writeBytes("Content-Disposition: form-data; name=\"file\"; filename=\"" + f.getName() + "\"" + lineEnd);
            dos.writeBytes("Content-Type: image/jpeg" + lineEnd + lineEnd);

            FileInputStream fis = new FileInputStream(f);
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = fis.read(buffer)) != -1) {
                dos.write(buffer, 0, bytesRead);
            }
            fis.close();
            dos.writeBytes(lineEnd);
        }

        dos.writeBytes(twoHyphens + boundary + twoHyphens + lineEnd);
        dos.flush();
        dos.close();

        int status = conn.getResponseCode();
        System.out.println("HTTP_STATUS: " + status);

        InputStream is = (status >= 200 && status < 400) ? conn.getInputStream() : conn.getErrorStream();
        BufferedReader reader = new BufferedReader(new InputStreamReader(is));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        reader.close();
        System.out.println("HTTP_RESPONSE: " + sb.toString());
    }
}

