#the tickets handeler
from .menu import Menu
from .menus import set_default_sounds
from .speech import speak
from . import consts

from functools import partial

class Tickets():
    def __init__(self, game):
        self.game=game
    
    def view_tickets(self, tickets):
        ticket_menu = Menu(self.game, "tickets", False, True, True, False)
        ticket_menu.add_items([
            ("submit a new ticket", self.create_ticket),
            ("view your tickets", lambda: self.list_tickets(tickets)),
            ("close", self.game.pop)
        ])
        set_default_sounds(ticket_menu)
        self.game.append(ticket_menu)

    def create_ticket(self):
        self.game.replace(self.game.input.run("Enter your ticket content", handeler=self.create_ticket2))
    
    def create_ticket2(self, message):
        if message.strip()=="": 
            speak("canceled")
            return self.game.pop()
        category_menu=Menu(self.game, "select the appropriate category for your ticket", autoclose=True)
        set_default_sounds(category_menu)
        category_menu.add_items([
            ("feedback", lambda: self.create_ticket3({
                "message":message,
                "category":"feedback"
            })),
            ("report", lambda: self.create_ticket3({
                "message":message,
                "category":"report"
            })),
            ("bug", lambda: self.create_ticket3({
                "message":message,
                "category":"bug"
            })),
            ("building", lambda: self.create_ticket3({
                "message":message,
                "category":"building"
            }))
        ])
        category_menu.add_items([("close", self.game.pop)])
        self.game.append(category_menu)
        
    
    def create_ticket3(self, ticket):
        self.game.network.send(consts.CHANNEL_MENUS, "submit_ticket", ticket)
        self.game.pop()

    def list_tickets(self, tickets):
        ticket_menu = Menu(self.game, "your tickets")
        set_default_sounds(ticket_menu)
        for ticket in tickets:
            ticket_menu.add_items([(f"{ticket['category']} {ticket['id']} - {ticket['author']} ({ticket['status']}): {ticket['message_list'][0]}. {len(ticket['message_list'])-1} replies. ", partial(self.view_ticket, ticket))])
        ticket_menu.add_items([("close", self.game.pop)])
        self.game.replace(ticket_menu)

    def view_ticket(self, ticket):
        ticket_menu = Menu(self.game, "your tickets")
        set_default_sounds(ticket_menu)
        ticket_menu.add_items([
            (f"ticket id: {ticket['id']}", lambda: None),
            (f"Author: {ticket['author']}", lambda: None),
            (f"Status: {ticket['status']}", lambda: None),
            (f"category: {ticket['category']}", lambda: None),
            (f"original message: {ticket['message_list'][0]}", lambda: self.edit_ticket(ticket))
        ])
        if len(ticket["message_list"])>1:
            for message in ticket["message_list"][1:]:
                ticket_menu.add_items([(message, lambda: None)])
        ticket_menu.add_items([
            ("send a message to this ticket", lambda: self.reply_ticket(ticket)),
            ("exit", self.game.pop)
        ])
        self.game.replace(ticket_menu)
    
    
    def edit_ticket(self, ticket):
        self.game.replace(self.game.input.run("edit your original message", default=ticket["message_list"][0], handeler=lambda message: self.edit_ticket2(ticket, message)))
    
    def edit_ticket2(self, ticket, message):
        if message.strip()=="":
            return self.game.cancel()
        ticket["message_list"][0]=message
        self.game.network.send(consts.CHANNEL_MENUS, "edit_ticket", {"ticket": ticket})
        self.game.pop()
    
    def reply_ticket(self, ticket):
        if ticket["status"] != "closed": self.game.replace(self.game.input.run("enter your reply", handeler=lambda message: self.reply_ticket2(ticket, message)))
        else: speak("You can't reply to closed tickets")
    
    def reply_ticket2(self, ticket, message):
        if message.strip()=="":
            return self.game.cancel()
        self.game.network.send(consts.CHANNEL_MENUS, "send_ticket_message", {
            "id": ticket["id"],
            "author": ticket["author"],
            "status": ticket["status"],
            "category": ticket["category"],
            "message_list": ticket["message_list"],
            "message": message
        })
        self.game.pop()