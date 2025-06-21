import re
import gradio as gr
import os
from dotenv import load_dotenv
import uuid

load_dotenv(override=True)

from research_assistant import graph as compiled_graph



def start_research(topic:str, max_analysts:int=3): 

    global thread_id
    thread_id = str(uuid.uuid4())

    clean_state = {
    "topic": topic,
    "max_analysts": max_analysts,
    "human_analyst_feedback": "",
    "analysts": [],
    "sections": [],
    "introduction": "",
    "content": "",
    "conclusion": "",
    "final_report": ""
    }

    try: 
        #thread = {"configurable": {"thread_id": "1"}}
        thread = {"configurable": {"thread_id": thread_id}}
        result=compiled_graph.invoke(clean_state, thread)

        return display_analysts_and_request_feedback(result)
    
    except Exception as e:

        return reset_to_start(result, f"❌ Error starting research: {str(e)}")

def display_analysts_and_request_feedback(result):
    analysts= result.get('analysts',[])
    if analysts:
        analysts_display="\n".join([
            f"**{i+1}. {analyst.name}**\n"
            f"   - Role: {analyst.role}\n"
            f"   - Affiliation: {analyst.affiliation}\n"
            f"   - Description: {analyst.description}\n"
            for i, analyst in enumerate(analysts)
        ])

        feedback_prompt = (
            f"## Analysts Generated for: '{result['topic']}'\n\n"
            f"{analysts_display}\n\n"
            f"**Please provide your feedback:**\n"
            f"- Type 'approve' to continue with these analysts\n"
            f"- Or provide specific feedback to regenerate analysts\n"
            f"- Example: 'Add a cybersecurity expert, remove the marketing analyst'"
        )

        return (
            feedback_prompt, 
            gr.update(visible=True, value=""),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=True)  # reset_btn   
            )
    
    else:
            return reset_to_start(result, "❌ No analysts generated. Please try again with a different topic.")


def continue_with_feedback(feedback):

    try:
        thread = {"configurable": {"thread_id": thread_id}}

        compiled_graph.update_state(
            thread,
            {"human_analyst_feedback": feedback},
            as_node="human_feedback"
        )
        
        result=compiled_graph.invoke(None, thread)
       

        state= compiled_graph.get_state(thread)

        print(state.next)
        print("hola esto es una prueba")

        if state.next and state.next[0] == "human_feedback":
             return display_analysts_and_request_feedback(result)
        else:
             print("Going to display final report")
             return display_final_report(result)
    except Exception as e:
         return reset_to_start(result, f"❌ Error processing feedback: {str(e)}")
    
def display_final_report(result):
    """Muestra el reporte final y resetea la interfaz"""
    print("Displaying final report...")
    try:
        final_report = result.get("final_report", "")
        print(f"Final report content: {final_report}")
        if final_report:
            return (
                f"## 📄 Final Research Report\n\n{final_report}",
                gr.update(visible=False),  # feedback_input
                gr.update(visible=False),  # continue_btn
                gr.update(visible=False),
                gr.update(visible=True)   
            )
        else:
            return reset_to_start(result, "❌ Error: No final report was generated.")
        
    except Exception as e:
        return reset_to_start(result, f"❌ Error displaying final report: {str(e)}")
            
def reset_to_start(result, message=""):
    """Resetea la interfaz al estado inicial"""
    return (
        message,
        gr.update(visible=False, value=""),  # feedback_input
        gr.update(visible=False),  # continue_btn
        gr.update(visible=False)    # start_btn
    )

def reset_interface():
 
    return (
        "",  # output1
        gr.update(visible=False, value=""),  # feedback_input
        gr.update(visible=False),  # continue_btn
        gr.update(visible=True),   # start_btn
        gr.update(visible=True, value=""),  # topic
        gr.update(visible=True)    # max_analysts
    )

############################################## Gradio UI #########################################################################
with gr.Blocks(title="Research Assistant", theme=gr.themes.Soft()) as app:
    gr.Markdown("<h1 style='font-size:2.8em; margin-bottom: 0.2em;'>🤖 Research Assistant</h1>")
    gr.Markdown("Assistant for researching complex topics. Process:\n"
    "1. Provide a research topic and the maximum number of analysts.\n"
    "2. The assistant will generate a summary of the analysts and their roles in the research.\n"
    "3. Provide feedback on the topics and the generated analysts.\n"
    "4. If you agree with the analysts, type 'approve' in the feedback field.\n"
    "5. The assistant will generate a final research report.\n\n")

    with gr.Row():
        with gr.Column(scale=3):
            topic_textbox = gr.Textbox(label="Topic to research", placeholder="Enter the topic you want to research", value="")

        with gr.Column(scale=1):
            max_analysts_slider = gr.Slider(minimum=1, maximum=5, step=1, value=3, label="Max Analysts", info="Maximum number of analysts to select for the research")

    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("#**Provide Feedback on the Analysts who will perform the research. If you want to approve the analysts, type 'approve' in the feedback box.")
            feedback_input = gr.Textbox(label="Feedback", placeholder="Provide your feedback or type 'approve' to continue", visible=False, value="")
            continue_btn = gr.Button("✅ Continue with Feedback", variant="primary", visible=False)
        with gr.Column(scale=1):
            reset_btn = gr.Button("🔄 Reset", variant="secondary", visible=False)

    with gr.Row():        
            start_button = gr.Button("🚀 Start Research", variant="primary", visible=True)
            # reset_btn = gr.Button("🔄 New Research", variant="secondary")  
    


    output1=gr.Markdown(label="Analysts Summary", value="")



    #########################################################################################

    start_button.click(
        fn=start_research,
        inputs=[topic_textbox, max_analysts_slider],
        outputs=[output1, feedback_input, continue_btn, start_button, reset_btn]
    )

    continue_btn.click(
        fn=continue_with_feedback,
        inputs=[feedback_input],
        outputs=[output1, feedback_input, continue_btn, start_button, reset_btn]
    )

    reset_btn.click(
        reset_interface,
        outputs=[output1, feedback_input, continue_btn, start_button, topic_textbox, max_analysts_slider]
    )

#################################################################################################################################

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.getenv("PORT", 8080))  # Changed default to match Dockerfile
    
    # Determine if we're in production (Railway) or development
    is_production = os.getenv("RAILWAY_ENVIRONMENT") is not None
    server_name = "0.0.0.0" if is_production else "127.0.0.1"
    
    # Launch the app
    print(f"Starting application on port {port}")
    print(f"Environment: {'Production (Railway)' if is_production else 'Development (Local)'}")
    print(f"🌐 Access the app at: http://{'0.0.0.0' if is_production else 'localhost'}:{port}")
    
    app.launch(
        server_name=server_name,
        server_port=port,
        share=False,
        show_error=True,
        inbrowser=not is_production,  # Don't auto-open browser in production
        quiet=is_production  # Reduce logging in production
    )

